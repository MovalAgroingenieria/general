# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    # Google Meet Integration Fields
    google_meet_url = fields.Char(
        string="Google Meet Link",
        help="Generated Google Meet link for this event"
    )
    google_event_id = fields.Char(
        string="Google Event ID",
        help="ID of the event in Google Calendar"
    )
    google_meet_generated = fields.Boolean(
        string="Google Meet Generated",
        default=False,
        help="Indicates if Google Meet link has been generated"
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate Meet links for appointment bookings"""
        events = super().create(vals_list)

        for event in events:
            # Only process events from appointment booking with Google Meet
            if event.booking_type_id:
                _logger.info(
                    f"Event has booking type: {event.booking_type_id.name}"
                )
                should_use = event.booking_type_id._should_use_google_meet()
                _logger.info(f"Should use Google Meet: {should_use}")

                if should_use and not event.google_meet_generated:
                    try:
                        _logger.info(
                            f"Attempting to generate Google Meet for event "
                            f"{event.id}"
                        )
                        event._generate_google_meet_link()
                    except Exception as e:
                        _logger.error(
                            f"Failed to generate Google Meet for event "
                            f"{event.id}: {e}",
                            exc_info=True
                        )
                        # Continue without Google Meet if generation fails
                        pass

        return events

    def write(self, vals):
        """Override write to update Google Meet events when needed"""
        result = super().write(vals)

        # Update Google Meet if date/time changes
        if any(field in vals for field in ['start', 'stop', 'name']):
            for event in self:
                if (event.google_event_id and
                    event.booking_type_id and
                        event.booking_type_id._should_use_google_meet()):

                    try:
                        event._update_google_meet_event()
                    except Exception as e:
                        _logger.error(
                            f"Failed to update Google Meet event {event.id}:"
                            f" {e}"
                        )

        return result

    def unlink(self):
        """Override unlink to delete Google Calendar events"""
        for event in self:
            if event.google_event_id:
                try:
                    event._delete_google_meet_event()
                except Exception as e:
                    _logger.error(
                        f"Failed to delete Google Meet event {event.id}: {e}"
                    )

        return super().unlink()

    def _generate_google_meet_link(self):
        """Generate Google Meet link for this event"""
        if (not self.booking_type_id or
                not self.booking_type_id._should_use_google_meet()):
            return False

        google_service = self.env['google.meet.service']

        # Prepare event data for Google Calendar
        attendees = []
        for attendee in self.attendee_ids:
            if attendee.email and '@' in attendee.email:
                attendees.append(attendee.email)

        # Format description using template
        description = self._format_meet_description()

        event_data = {
            'summary': self.name or 'Appointment',
            'description': description,
            'start_datetime': self.start.isoformat(),
            'end_datetime': self.stop.isoformat(),
            'attendees': attendees,
        }

        try:
            result = google_service.create_meet_event(event_data)

            if result.get('success'):
                # Update event with Google Meet info
                self.write({
                    'google_meet_url': result['meet_link'],
                    'google_event_id': result['google_event_id'],
                    'google_meet_generated': True,
                    'meeting_url': result['meet_link'],
                })

                _logger.info(
                    f"Generated Google Meet link for event {self.id}: "
                    f"{result['meet_link']}"
                )
                return result['meet_link']
            else:
                raise UserError(_("Failed to generate Google Meet link"))

        except Exception as e:
            _logger.error(f"Error generating Google Meet for event {self.id}:"
                          f" {e}")
            raise UserError(_(
                "Could not generate Google Meet link: %s"
            ) % str(e))

    def _update_google_meet_event(self):
        """Update Google Calendar event"""
        if not self.google_event_id:
            return False

        google_service = self.env['google.meet.service']

        event_data = {
            'summary': self.name or 'Appointment',
            'description': self._format_meet_description(),
            'start_datetime': self.start.isoformat(),
            'end_datetime': self.stop.isoformat(),
        }

        result = google_service.update_meet_event(
            self.google_event_id,
            event_data
        )

        if result.get('success'):
            _logger.info(f"Updated Google Meet event {self.google_event_id}")

        return result.get('success', False)

    def _delete_google_meet_event(self):
        """Delete Google Calendar event"""
        if not self.google_event_id:
            return False

        google_service = self.env['google.meet.service']
        result = google_service.delete_meet_event(self.google_event_id)

        if result.get('success'):
            _logger.info(f"Deleted Google Meet event {self.google_event_id}")

        return result.get('success', False)

    def _format_meet_description(self):
        """Format meeting description using booking type template"""
        if not self.booking_type_id:
            return self.description or ""

        template = (
            self.booking_type_id.google_meet_description_template or
            self.description or ""
        )

        # Get partner name from attendees
        partner_name = "Client"
        if self.partner_ids:
            partner_name = self.partner_ids[0].name or "Client"

        # Format template with available data
        try:
            format_data = {
                'name': self.name or "Appointment",
                'partner_name': partner_name,
                'start_date': (
                    self.start.strftime("%Y-%m-%d %H:%M") if self.start else ""
                ),
                'duration': self.booking_type_id.booking_duration or 1,
                'meet_link': self.google_meet_url or "To be generated"
            }
            return template.format(**format_data)
        except (KeyError, ValueError):
            # Fallback if template formatting fails
            return (
                self.description or f"Appointment: {self.name or 'Meeting'}"
            )

    def action_regenerate_google_meet(self):
        """Manual action to regenerate Google Meet link"""
        for event in self:
            if (not event.booking_type_id or
                    not event.booking_type_id._should_use_google_meet()):
                raise UserError(_(
                    "Google Meet is not enabled for this booking type"
                ))

            # Delete existing Google event if present
            if event.google_event_id:
                event._delete_google_meet_event()

            # Reset flags and regenerate
            event.write({
                'google_meet_generated': False,
                'google_event_id': False,
                'google_meet_url': False,
            })

            event._generate_google_meet_link()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Success!"),
                'message': _("Google Meet link has been regenerated."),
                'type': 'success',
            }
        }
