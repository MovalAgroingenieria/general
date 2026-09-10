# 2025 Moval Agroingenieria
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, api, fields, models
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    attendee_sync_enabled = fields.Boolean(
        'Sync with Attendees',
        default=True,
        help=(
            'Enable the additional attendee synchronization controls for this '
            'event. Google Calendar still uses the canonical event and its '
            'attendee list; no per-attendee copies are created.'
        ),
    )
    last_attendee_sync = fields.Datetime(
        'Last Attendee Synchronization',
        readonly=True,
    )
    sync_errors = fields.Text(
        'Synchronization Errors',
        readonly=True,
    )

    def _attendee_google_users(self):
        """Return Google-enabled internal users related to this event.

        The organizer is included when Google Calendar is configured. Attendee
        users are included only when their additional attendee synchronization
        flag is enabled.

        This method deliberately returns users, not Google event ids. The
        canonical Google identity is ``calendar.event.google_id`` managed by
        Odoo's ``google_calendar`` addon.
        """
        self.ensure_one()

        organizer = self.user_id.sudo().filtered(
            lambda user: (
                not user.share
                and user.google_calendar_rtoken
                and not user.google_synchronization_stopped
            )
        )

        attendee_users = self.attendee_ids.mapped(
            'partner_id.user_ids'
        ).sudo().filtered(
            lambda user: (
                not user.share
                and user.google_calendar_attendee_sync
                and user.google_calendar_rtoken
                and not user.google_synchronization_stopped
            )
        )

        return organizer | attendee_users

    def _sync_attendees_calendars(self):
        """Synchronize using Odoo's native Google Calendar engine.

        No attendee-specific Google event is inserted here. Odoo synchronizes
        one canonical ``calendar.event`` / ``google_id`` and Google distributes
        that event to the attendees contained in the event payload.
        """
        google_service = GoogleCalendarService(self.env['google.service'])

        for event in self:
            if not event.attendee_sync_enabled or not event.attendee_ids:
                continue

            errors = []
            users = event._attendee_google_users()

            for user in users:
                try:
                    # Keep exactly the same execution pattern used by Odoo's
                    # native Google Calendar cron. This method performs both
                    # Google -> Odoo and Odoo -> Google reconciliation and uses
                    # calendar.event.google_id as the canonical identity.
                    user.with_user(user).sudo()._sync_google_calendar(
                        google_service
                    )
                except Exception as exc:
                    error = _(
                        'Error synchronizing Google Calendar for %(user)s: %(error)s',
                        user=user.name,
                        error=str(exc),
                    )
                    errors.append(error)
                    _logger.exception(
                        'Attendee calendar synchronization failed for event %s '
                        '(id=%s), user %s (id=%s)',
                        event.name,
                        event.id,
                        user.name,
                        user.id,
                    )

            event.sudo().write({
                'last_attendee_sync': fields.Datetime.now(),
                'sync_errors': '\n'.join(errors) if errors else False,
            })

            if errors:
                event.message_post(
                    body=_(
                        'Attendee synchronization errors:<br/>%s',
                        '<br/>'.join(errors),
                    ),
                    message_type='notification',
                )

        return True

    def action_sync_attendees(self):
        """Manually run native Google Calendar reconciliation."""
        self.ensure_one()

        if not self.attendee_ids:
            raise UserError(_('This event has no attendees to synchronize.'))

        self._sync_attendees_calendars()

        if self.sync_errors:
            notification_type = 'warning'
            message = _(
                'Synchronization finished with errors. Check the event '
                'synchronization log.'
            )
        else:
            notification_type = 'success'
            message = _(
                'Google Calendar synchronization completed without creating '
                'attendee-specific event copies.'
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Synchronization completed'),
                'message': message,
                'type': notification_type,
            },
        }

    @api.model
    def _cron_sync_attendee_events(self):
        """Compatibility cron: delegate to the single native-based user cron."""
        return self.env['res.users']._cron_sync_attendee_events_all_users()

    def action_mass_sync_attendees(self):
        """Synchronize selected events without creating Google copies."""
        active_ids = self.env.context.get('active_ids', [])
        events = self.browse(active_ids).exists()

        if not events:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Events Selected'),
                    'message': _('Please select events to synchronize.'),
                    'type': 'warning',
                },
            }

        users = self.env['res.users'].sudo()
        target_events = events.filtered(
            lambda event: (
                event.active
                and event.attendee_sync_enabled
                and event.attendee_ids
            )
        )
        for event in target_events:
            users |= event._attendee_google_users()

        google_service = GoogleCalendarService(self.env['google.service'])
        errors = []
        synchronized_users = 0

        for user in users:
            try:
                user.with_user(user).sudo()._sync_google_calendar(google_service)
                synchronized_users += 1
            except Exception as exc:
                errors.append('%s: %s' % (user.name, exc))
                _logger.exception(
                    'Mass attendee calendar synchronization failed for user %s '
                    '(id=%s)',
                    user.name,
                    user.id,
                )

        target_events.sudo().write({
            'last_attendee_sync': fields.Datetime.now(),
            'sync_errors': '\n'.join(errors) if errors else False,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Bulk Synchronization Complete'),
                'message': _(
                    'Processed %(events)s events with %(users)s Google users. '
                    'Errors: %(errors)s.',
                    events=len(target_events),
                    users=synchronized_users,
                    errors=len(errors),
                ),
                'type': 'success' if not errors else 'warning',
            },
        }
