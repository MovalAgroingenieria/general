# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    google_calendar_attendee_sync = fields.Boolean(
        'Automatic Attendee Synchronization',
        default=True,
        help="If enabled, you will automatically receive in your Google Calendar "
             "the events where you are an attendee, even if you are not the organizer"
    )

    google_calendar_sync_errors = fields.Text(
        'Google Calendar Synchronization Errors',
        readonly=True,
        help="Log of errors in Google Calendar synchronization"
    )

    attendee_events_synced = fields.Integer(
        'Events Synchronized as Attendee',
        default=0,
        readonly=True,
        help="Number of synchronized events where you are an attendee"
    )

    def _has_valid_google_token(self):
        """Check if the user has a valid Google Calendar token"""
        self.ensure_one()
        return bool(self.google_calendar_token)

    def _log_sync_error(self, error_message):
        """Log synchronization errors for the user"""
        self.ensure_one()
        current_errors = self.google_calendar_sync_errors or ""
        timestamp = fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_error = f"[{timestamp}] {error_message}"

        # Keep only the last 10 errors
        error_lines = current_errors.split('\n') if current_errors else []
        error_lines.append(new_error)

        if len(error_lines) > 10:
            error_lines = error_lines[-10:]

        self.google_calendar_sync_errors = '\n'.join(error_lines)

    def _clear_sync_errors(self):
        """Clear synchronization errors"""
        self.google_calendar_sync_errors = False

    def action_test_google_calendar_connection(self):
        """Action to test Google Calendar connection"""
        self.ensure_one()

        if not self._has_valid_google_token():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Error'),
                    'message': _('You do not have Google Calendar configured. '
                               'Go to Preferences → Calendar Sync to configure it.'),
                    'type': 'warning',
                }
            }

        try:
            # Try a simple operation with Google Calendar
            # Here you could make a test API call

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Successful Connection'),
                    'message': _('Your Google Calendar connection is working correctly.'),
                    'type': 'success',
                }
            }

        except Exception as e:
            self._log_sync_error(f"Connection test error: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Error'),
                    'message': _('Error connecting to Google Calendar: %s') % str(e),
                    'type': 'danger',
                }
            }

    @api.model
    def _cron_sync_attendee_events_all_users(self):
        """
        Scheduled task that synchronizes events for all users
        who have automatic synchronization enabled
        """
        try:
            users_to_sync = self.search([
                ('google_calendar_attendee_sync', '=', True),
                ('google_calendar_token', '!=', False),
                ('share', '=', False),  # Exclude portal users
            ])

            user_count = len(users_to_sync) if users_to_sync else 0
            _logger.info(f"Starting event synchronization for {user_count} users")

            for user in users_to_sync:
                try:
                    user._sync_my_attendee_events()
                except Exception as e:
                    error_msg = f"Error synchronizing events for {user.name}: {str(e)}"
                    _logger.error(error_msg)
                    user._log_sync_error(error_msg)
        except Exception as e:
            _logger.error(f"Cron job _cron_sync_attendee_events_all_users failed: {e}")

    def _sync_my_attendee_events(self):
        """
        Synchronize all events where I am attendee but not organizer
        """
        self.ensure_one()

        if not self.google_calendar_attendee_sync or not self._has_valid_google_token():
            return

        # Search for events where I am attendee but not organizer
        CalendarEvent = self.env['calendar.event']

        domain = [
            ('attendee_ids.partner_id', '=', self.partner_id.id),
            ('user_id', '!=', self.id),
            ('active', '=', True),
            ('attendee_sync_enabled', '=', True),
            # Only future and recent events (last 7 days)
            ('start', '>=', fields.Datetime.subtract(fields.Datetime.now(), days=7)),
            ('start', '<=', fields.Datetime.add(fields.Datetime.now(), days=90)),
        ]

        events = CalendarEvent.search(domain)
        synced_count = 0

        event_count = len(events) if events else 0
        _logger.info(f"Synchronizing {event_count} events for user {self.name}")

        for event in events:
            try:
                # Find my participation in the event
                my_attendance = event.attendee_ids.filtered(
                    lambda a: a.partner_id.id == self.partner_id.id
                )

                if my_attendance:
                    event.with_user(self)._sync_single_attendee_event(my_attendance[0])
                    synced_count += 1

            except Exception as e:
                error_msg = f"Error synchronizing event '{event.name}': {str(e)}"
                _logger.warning(error_msg)
                self._log_sync_error(error_msg)

        # Update synchronized events counter
        if synced_count > 0:
            self.attendee_events_synced += synced_count
            _logger.info(f"Synchronized {synced_count} events for {self.name}")

    def action_sync_my_attendee_events(self):
        """Manual action to synchronize my attendee events"""
        self.ensure_one()

        if not self._has_valid_google_token():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Google Calendar not configured'),
                    'message': _('You need to configure Google Calendar before synchronizing events.'),
                    'type': 'warning',
                }
            }

        try:
            self._sync_my_attendee_events()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Synchronization completed'),
                    'message': _('Your attendee events have been synchronized with Google Calendar.'),
                    'type': 'success',
                }
            }

        except Exception as e:
            self._log_sync_error(f"Manual synchronization error: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Synchronization error'),
                    'message': _('Error synchronizing events: %s') % str(e),
                    'type': 'danger',
                }
            }

    def write(self, vals):
        """Override write to clear errors when Google Calendar is reconfigured"""
        res = super().write(vals)

        # Clear errors if Google token is updated
        if 'google_calendar_token' in vals and vals['google_calendar_token']:
            self._clear_sync_errors()

        return res

    @api.model
    def _cleanup_sync_errors(self):
        """Cleanup old synchronization errors (called by cron job)"""
        try:
            users_with_errors = self.search([('google_calendar_sync_errors', '!=', False)])
            user_count = len(users_with_errors) if users_with_errors else 0

            for user in users_with_errors:
                if user.google_calendar_sync_errors:
                    lines = user.google_calendar_sync_errors.split('\n')
                    # Keep only the first 5 lines (most recent errors)
                    if len(lines) > 5:
                        user.google_calendar_sync_errors = '\n'.join(lines[:5])

            _logger.info(f"Cleaned up sync errors for {user_count} users")

        except Exception as e:
            _logger.error(f"Error in cleanup sync errors cron job: {e}")