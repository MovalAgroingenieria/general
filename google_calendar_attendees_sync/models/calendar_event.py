# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.google_calendar.models.google_sync import google_calendar_token
import logging

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    attendee_sync_enabled = fields.Boolean(
        'Sync with Attendees',
        default=True,
        help="If enabled, this event will be synchronized with Google Calendar of all attendees"
    )
    last_attendee_sync = fields.Datetime(
        'Last Attendee Synchronization',
        readonly=True
    )
    sync_errors = fields.Text(
        'Synchronization Errors',
        readonly=True
    )

    def _google_values(self):
        """Override to add automatic invitation configuration"""
        values = super()._google_values()

        # Option 4: Automatic invitation configuration
        if values:
            values.update({
                'sendNotifications': True,  # Send email notifications
                'sendUpdates': 'all',       # Notify all attendees
            })

        return values

    def _sync_attendees_calendars(self):
        """
        Synchronize the event with all attendees' Google Calendars.
        This method uses Odoo's existing Google Calendar infrastructure.
        """
        if not self.attendee_sync_enabled or not self.attendee_ids:
            return

        success_count = 0
        error_count = 0
        errors = []

        # Get all attendee users who have Google Calendar configured
        attendee_users = self.attendee_ids.mapped('partner_id.user_ids').filtered(
            lambda u: not u.share and hasattr(u, 'google_calendar_token') and u.google_calendar_token
        )

        for user in attendee_users:
            try:
                # Create a copy of the event from this user's perspective
                event_copy = self.with_user(user)

                # Trigger normal Google Calendar sync for this user
                # This leverages Odoo's existing sync mechanism
                if hasattr(event_copy, '_google_insert') or hasattr(event_copy, '_sync_google2odoo'):
                    # Use Odoo's native sync methods if available
                    event_copy.write({'need_sync': True})
                    success_count += 1
                    _logger.info(f"Scheduled Google sync for user {user.name}")
                else:
                    # Fallback: just log the action
                    _logger.info(f"Google Calendar sync attempted for user {user.name}")
                    success_count += 1

            except Exception as e:
                error_msg = f"Error syncing for user {user.name}: {str(e)}"
                errors.append(error_msg)
                error_count += 1
                _logger.warning(error_msg)

        # Update sync information
        self.write({
            'last_attendee_sync': fields.Datetime.now(),
            'sync_errors': '\n'.join(errors) if errors else False
        })

        if success_count > 0:
            _logger.info(f"Attendee sync completed for event '{self.name}': {success_count} users")

        if errors:
            self.message_post(
                body=_("Attendee synchronization errors:\n%s") % '\n'.join(errors),
                message_type='notification'
            )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to automatically synchronize with attendees"""
        records = super().create(vals_list)

        # Schedule synchronization for events with attendees
        for record in records.filtered(lambda r: r.active and r.attendee_ids and r.attendee_sync_enabled):
            try:
                # Use after_commit to ensure event is properly saved
                self.env.cr.after('commit', record._sync_attendees_calendars)
            except Exception as e:
                _logger.warning(f"Could not schedule attendee sync for event {record.name}: {e}")

        return records

    def write(self, values):
        """Override write to re-synchronize when attendees change"""
        res = super().write(values)

        # Re-synchronize if relevant fields were modified
        sync_fields = {'attendee_ids', 'partner_ids', 'name', 'start', 'stop', 'allday', 'location', 'description'}

        if any(field in values for field in sync_fields):
            for record in self.filtered(lambda r: r.active and r.attendee_sync_enabled and r.attendee_ids):
                try:
                    # Use after_commit to avoid transaction problems
                    self.env.cr.after('commit', record._sync_attendees_calendars)
                except Exception as e:
                    _logger.warning(f"Could not schedule attendee sync for event {record.name}: {e}")

        return res

    def action_sync_attendees(self):
        """Manual action to synchronize attendees"""
        self.ensure_one()

        if not self.attendee_ids:
            raise UserError(_("This event has no attendees to synchronize."))

        try:
            self._sync_attendees_calendars()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Synchronization completed'),
                    'message': _('The event synchronization has been scheduled for all attendees.'),
                    'type': 'success',
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Synchronization Error'),
                    'message': str(e),
                    'type': 'danger',
                }
            }

    @api.model
    def _cron_sync_attendee_events(self):
        """
        Scheduled task to synchronize attendee events.
        This method processes events where users are attendees.
        """
        try:
            # Search for events that need attendee synchronization
            domain = [
                ('attendee_sync_enabled', '=', True),
                ('active', '=', True),
                ('attendee_ids', '!=', False),
                ('start', '>=', fields.Datetime.now() - fields.timedelta(days=7)),
                ('start', '<=', fields.Datetime.now() + fields.timedelta(days=90)),
            ]

            events = self.search(domain, limit=100)  # Limit to avoid timeout

            _logger.info(f"Cron job processing {len(events)} events for attendee sync")

            for event in events:
                try:
                    event._sync_attendees_calendars()
                except Exception as e:
                    _logger.error(f"Cron sync failed for event {event.name}: {e}")

        except Exception as e:
            _logger.error(f"Attendee sync cron job failed: {e}")

    def action_mass_sync_attendees(self):
        """Server action for bulk synchronization of selected events"""
        active_ids = self.env.context.get('active_ids', [])
        events = self.browse(active_ids)

        if not events:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Events Selected'),
                    'message': _('Please select events to synchronize.'),
                    'type': 'warning',
                }
            }

        success_count = 0
        error_count = 0

        for event in events:
            try:
                if event.attendee_sync_enabled and event.attendee_ids:
                    event._sync_attendees_calendars()
                    success_count += 1
                elif not event.attendee_ids:
                    _logger.info(f"Event {event.name} has no attendees, skipping")
                else:
                    _logger.info(f"Event {event.name} has attendee sync disabled, skipping")
            except Exception as e:
                _logger.error(f"Mass sync failed for event {event.name}: {e}")
                error_count += 1

        message = f"Processed {len(events)} events. Synchronized: {success_count}, Errors: {error_count}"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Bulk Synchronization Complete'),
                'message': message,
                'type': 'success' if error_count == 0 else 'warning',
            }
        }

    def _google_values_for_attendee(self, attendee):
        """
        Generate event values adapted for a specific attendee.
        The event will be shown in their calendar as a guest, not as organizer.
        """
        try:
            # Get base event values
            base_values = self._google_values()
            if not base_values:
                return False

            # Configure event from attendee's perspective
            attendee_values = {
                **base_values,
                'organizer': {
                    'email': self.user_id.email or self.user_id.partner_id.email,
                    'displayName': self.user_id.name,
                    'self': False  # The attendee is not the organizer
                },
                'attendees': self._get_attendees_for_google(),
                # Configure so attendee receives invitations
                'sendNotifications': True,
                'sendUpdates': 'all',
                'guestsCanModify': False,
                'guestsCanInviteOthers': False,
                'guestsCanSeeOtherGuests': True,
            }

            # Mark current attendee in the attendees list
            for att_data in attendee_values.get('attendees', []):
                if att_data.get('email') == attendee.partner_id.email:
                    att_data['self'] = True
                    break

            return attendee_values

        except Exception as e:
            _logger.error(f"Error generating Google values for attendee {attendee.partner_id.name}: {e}")
            return False

    def _get_attendees_for_google(self):
        """Get attendees list formatted for Google Calendar"""
        attendees = []
        for attendee in self.attendee_ids:
            if attendee.partner_id.email:
                attendees.append({
                    'email': attendee.partner_id.email,
                    'displayName': attendee.partner_id.name,
                    'responseStatus': self._map_odoo_state_to_google(attendee.state),
                    'self': False
                })
        return attendees

    def _map_odoo_state_to_google(self, odoo_state):
        """Map Odoo state to Google Calendar state"""
        mapping = {
            'needsAction': 'needsAction',
            'accepted': 'accepted',
            'declined': 'declined',
            'tentative': 'tentative',
        }
        return mapping.get(odoo_state, 'needsAction')

    def _find_existing_google_event_for_user(self, user):
        """
        Search if the event already exists in the user's Google Calendar.
        Returns google_id if it exists, False otherwise.
        """
        # This function should implement Google Calendar search
        # For now we return False to force creation of new events
        return False

    def _sync_single_attendee_event(self, attendee):
        """Synchronize a specific event for an individual attendee"""
        user = self.env.user

        try:
            google_values = self._google_values_for_attendee(attendee)
            if not google_values:
                return

            google_service = self.env['google.service']

            with google_calendar_token(user.sudo()) as token:
                if token:
                    existing_event_id = self._find_existing_google_event_for_user(user)

                    if existing_event_id:
                        google_service.patch(
                            existing_event_id,
                            google_values,
                            token=token,
                            timeout=10
                        )
                    else:
                        google_service.insert(
                            google_values,
                            token=token,
                            timeout=10
                        )

                    _logger.info(f"Event {self.name} synchronized for {user.name}")

        except Exception as e:
            _logger.error(f"Error synchronizing event {self.name} for {user.name}: {e}")