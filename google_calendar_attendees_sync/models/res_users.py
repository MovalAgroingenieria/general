# 2025 Moval Agroingenieria
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, api, fields, models
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService
from odoo.loglevels import exception_to_unicode

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    google_calendar_attendee_sync = fields.Boolean(
        'Automatic Attendee Synchronization',
        default=True,
        help=(
            'Run the additional two-hour Google Calendar reconciliation for '
            'this user. Synchronization uses Odoo native Google Calendar logic '
            'and never creates attendee-specific copies.'
        ),
    )

    google_calendar_sync_errors = fields.Text(
        'Google Calendar Synchronization Errors',
        readonly=True,
        help='Log of errors in Google Calendar synchronization',
    )

    attendee_events_synced = fields.Integer(
        'Events Synchronized as Attendee',
        default=0,
        readonly=True,
        help=(
            'Current number of active recent/future Odoo events where this '
            'user is an attendee and not the organizer.'
        ),
    )

    def _has_valid_google_token(self):
        """Return whether Google Calendar can refresh/authenticate this user."""
        self.ensure_one()
        return bool(
            self.sudo().google_calendar_rtoken
            and not self.sudo().google_synchronization_stopped
        )

    def _attendee_event_domain(self):
        """Domain used only for attendee diagnostics/counter."""
        self.ensure_one()
        return [
            ('attendee_ids.partner_id', '=', self.partner_id.id),
            ('user_id', '!=', self.id),
            ('active', '=', True),
            ('attendee_sync_enabled', '=', True),
            ('start', '>=', fields.Datetime.subtract(fields.Datetime.now(), days=7)),
            ('start', '<=', fields.Datetime.add(fields.Datetime.now(), days=90)),
        ]

    def _log_sync_error(self, error_message):
        """Keep only the ten most recent synchronization errors."""
        self.ensure_one()
        current_errors = self.sudo().google_calendar_sync_errors or ''
        timestamp = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_error = '[%s] %s' % (timestamp, error_message)

        error_lines = current_errors.split('\n') if current_errors else []
        error_lines.append(new_error)
        error_lines = error_lines[-10:]

        self.sudo().write({
            'google_calendar_sync_errors': '\n'.join(error_lines),
        })

    def _clear_sync_errors(self):
        """Clear synchronization errors without triggering custom recursion."""
        self.ensure_one()
        self.sudo().write({'google_calendar_sync_errors': False})

    def _update_attendee_event_counter(self):
        self.ensure_one()
        count = self.env['calendar.event'].sudo().search_count(
            self._attendee_event_domain()
        )
        self.sudo().write({'attendee_events_synced': count})
        return count

    def action_test_google_calendar_connection(self):
        """Refresh/read the Google token without creating calendar events."""
        self.ensure_one()

        if not self._has_valid_google_token():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Error'),
                    'message': _(
                        'You do not have Google Calendar configured. Go to '
                        'Preferences -> Calendar Sync to configure it.'
                    ),
                    'type': 'warning',
                },
            }

        try:
            token = self.sudo()._get_google_calendar_token()
            if not token:
                raise ValueError(_('Google Calendar did not return an access token.'))

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Successful Connection'),
                    'message': _('Your Google Calendar token is available.'),
                    'type': 'success',
                },
            }
        except Exception as exc:
            self._log_sync_error(
                _('Connection test error: %s', str(exc))
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Error'),
                    'message': _('Error connecting to Google Calendar: %s', str(exc)),
                    'type': 'danger',
                },
            }

    @api.model
    def _cron_sync_attendee_events_all_users(self):
        """Run Odoo's native Google synchronization every two hours.

        The old implementation manually inserted one Google event per attendee.
        That broke the one-Odoo-event/one-Google-id invariant and caused HTTP
        409 duplicate errors. This cron delegates to Odoo's native reconciler,
        which matches Google events by ``google_id`` and uses the organizer's
        canonical event/attendee list.
        """
        users_to_sync = self.sudo().search([
            ('google_calendar_attendee_sync', '=', True),
            ('google_calendar_rtoken', '!=', False),
            ('google_synchronization_stopped', '=', False),
            ('share', '=', False),
        ])

        google_service = GoogleCalendarService(self.env['google.service'])
        _logger.info(
            'Starting native attendee Google Calendar reconciliation for %s users',
            len(users_to_sync),
        )

        for user in users_to_sync:
            try:
                _logger.info(
                    'Attendee Calendar Sync - starting for %s (id=%s)',
                    user.login,
                    user.id,
                )

                # Same call pattern used by google_calendar's native cron.
                user.with_user(user).sudo()._sync_google_calendar(google_service)
                user._update_attendee_event_counter()
                user._clear_sync_errors()

                # Isolate users exactly as the native Odoo cron does. A problem
                # in one Google account must not roll back all other accounts.
                self.env.cr.commit()

            except Exception as exc:
                self.env.cr.rollback()
                error_msg = _(
                    'Error synchronizing events for %(user)s: %(error)s',
                    user=user.name,
                    error=exception_to_unicode(exc),
                )
                _logger.exception(error_msg)

                # Re-browse after rollback before recording diagnostics.
                failed_user = self.sudo().browse(user.id).exists()
                if failed_user:
                    try:
                        failed_user._log_sync_error(error_msg)
                        self.env.cr.commit()
                    except Exception:
                        self.env.cr.rollback()
                        _logger.exception(
                            'Could not persist Google Calendar synchronization '
                            'error for user id=%s',
                            user.id,
                        )

        return True

    def _sync_my_attendee_events(self):
        """Run native Google reconciliation for the current user.

        This method intentionally does not iterate Odoo events and never calls
        ``GoogleCalendarService.insert`` itself. Odoo's native synchronization
        decides whether the canonical event needs INSERT/PATCH based on
        ``calendar.event.google_id`` and ``need_sync``.
        """
        self.ensure_one()

        if not self.google_calendar_attendee_sync or not self._has_valid_google_token():
            return False

        google_service = GoogleCalendarService(self.env['google.service'])

        try:
            result = self.with_user(self).sudo()._sync_google_calendar(google_service)
            self._update_attendee_event_counter()
            self._clear_sync_errors()
            return result
        except Exception as exc:
            error_msg = _(
                'Error synchronizing events for %(user)s: %(error)s',
                user=self.name,
                error=exception_to_unicode(exc),
            )
            self._log_sync_error(error_msg)
            _logger.exception(error_msg)
            raise

    def action_sync_my_attendee_events(self):
        """Manual native synchronization for this Google Calendar user."""
        self.ensure_one()

        if not self._has_valid_google_token():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Google Calendar not configured'),
                    'message': _(
                        'You need to configure Google Calendar before '
                        'synchronizing events.'
                    ),
                    'type': 'warning',
                },
            }

        try:
            self._sync_my_attendee_events()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Synchronization completed'),
                    'message': _(
                        'Google Calendar was reconciled using the canonical '
                        'Odoo event ids.'
                    ),
                    'type': 'success',
                },
            }
        except Exception as exc:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Synchronization error'),
                    'message': _('Error synchronizing events: %s', str(exc)),
                    'type': 'danger',
                },
            }

    def write(self, vals):
        """Clear historical custom errors when Google is reconfigured."""
        res = super().write(vals)
        if 'google_calendar_account_id' in vals and vals['google_calendar_account_id']:
            for user in self:
                user._clear_sync_errors()
        return res

    @api.model
    def _cleanup_sync_errors(self):
        """Keep the five most recent custom synchronization errors."""
        users_with_errors = self.sudo().search([
            ('google_calendar_sync_errors', '!=', False),
        ])

        for user in users_with_errors:
            lines = (user.google_calendar_sync_errors or '').split('\n')
            if len(lines) > 5:
                user.sudo().write({
                    'google_calendar_sync_errors': '\n'.join(lines[-5:]),
                })

        _logger.info('Cleaned up sync errors for %s users', len(users_with_errors))
        return True
