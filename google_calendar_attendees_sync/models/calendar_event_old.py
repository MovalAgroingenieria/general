# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
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
                    'self': False  # El participante no es el organizador
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
            _logger.error(f"Error generando valores de Google para participante {attendee.partner_id.name}: {e}")
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

    def _sync_attendees_calendars(self):
        """
        Synchronize the event in each attendee's Google Calendar.
        This is the implementation of Option 1.
        """
        if not self.attendee_sync_enabled:
            return

        errors = []
        success_count = 0
        google_service = self.env['google.service']

        for attendee in self.attendee_ids:
            # Search for valid user with Google token
            user = attendee.partner_id.user_ids.filtered(
                lambda u: not u.share and u.google_calendar_token
            )

            if not user:
                continue

            user = user[0]  # Take first valid user

            try:
                # Generate specific values for this attendee
                google_values = self._google_values_for_attendee(attendee)
                if not google_values:
                    continue

                # Synchronize with attendee's token
                with google_calendar_token(user.sudo()) as token:
                    if token:
                        # Check if event already exists in user's calendar
                        existing_event_id = self._find_existing_google_event_for_user(user)

                        if existing_event_id:
                            # Update existing event
                            google_service.patch(
                                existing_event_id,
                                google_values,
                                token=token,
                                timeout=10
                            )
                        else:
                            # Create new event
                            result = google_service.insert(
                                google_values,
                                token=token,
                                timeout=10
                            )

                        success_count += 1
                        _logger.info(f"Evento sincronizado exitosamente para {user.name}")

            except Exception as e:
                error_msg = f"Error sincronizando evento para {user.name}: {str(e)}"
                errors.append(error_msg)
                _logger.warning(error_msg)

        # Update synchronization information
        self.write({
            'last_attendee_sync': fields.Datetime.now(),
            'sync_errors': '\n'.join(errors) if errors else False
        })

        if errors:
            # Show error notification to organizer
            self.message_post(
                body=_("Google Calendar synchronization errors:\n%s") % '\n'.join(errors),
                message_type='notification'
            )

    def _find_existing_google_event_for_user(self, user):
        """
        Search if the event already exists in the user's Google Calendar.
        Returns google_id if it exists, False otherwise.
        """
        # This function should implement Google Calendar search
        # For now we return False to force creation of new events
        return False

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to automatically synchronize with attendees"""
        records = super().create(vals_list)

        # Synchronize active events with attendees
        for record in records.filtered(lambda r: r.active and r.attendee_ids):
            if record.attendee_sync_enabled:
                # Use after_commit to ensure event is saved
                self.env.cr.after('commit', record._sync_attendees_calendars)

        return records

    def write(self, values):
        """Override write to re-synchronize when attendees change"""
        res = super().write(values)

        # Re-synchronize if relevant fields were modified
        sync_fields = {'attendee_ids', 'partner_ids', 'name', 'start', 'stop', 'allday', 'location'}
        if values.keys() & sync_fields:
            for record in self.filtered(lambda r: r.active and r.attendee_sync_enabled):
                # Use after_commit to avoid transaction problems
                self.env.cr.after('commit', record._sync_attendees_calendars)

        return res

    def action_sync_attendees(self):
        """Manual action to synchronize attendees"""
        self.ensure_one()
        if not self.attendee_ids:
            raise UserError(_("This event has no attendees to synchronize."))

        self._sync_attendees_calendars()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Synchronization completed'),
                'message': _('The event has been synchronized with the attendees\' Google Calendars.'),
                'type': 'success',
            }
        }

    @api.model
    def _cron_sync_attendee_events(self):
        """
        Scheduled task to synchronize attendee events.
        Search for events where current user is attendee but not organizer.
        """
        # Search for events where I am attendee but not organizer
        domain = [
            ('attendee_ids.partner_id.user_ids', 'in', self.env.user.id),
            ('user_id', '!=', self.env.user.id),
            ('active', '=', True),
            ('attendee_sync_enabled', '=', True),
            ('start', '>=', fields.Datetime.now().replace(hour=0, minute=0, second=0)),
            ('start', '<=', fields.Datetime.add(fields.Datetime.now(), days=30)),
        ]

        events = self.search(domain)

        for event in events:
            # Search for my attendance in the event
            my_attendance = event.attendee_ids.filtered(
                lambda a: self.env.user in a.partner_id.user_ids
            )

            if my_attendance and self.env.user.google_calendar_token:
                try:
                    event.with_user(self.env.user)._sync_single_attendee_event(my_attendance[0])
                except Exception as e:
                    _logger.warning(f"Error en cron sync para evento {event.name}: {e}")

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

                    _logger.info(f"Evento {self.name} sincronizado para {user.name}")

        except Exception as e:
            _logger.error(f"Error sincronizando evento {self.name} para {user.name}: {e}")
