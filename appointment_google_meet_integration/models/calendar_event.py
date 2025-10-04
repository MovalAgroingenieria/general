# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

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
                should_use = event.booking_type_id._should_use_google_meet()

                if should_use and not event.google_meet_generated:
                    try:
                        meet_link = event._generate_google_meet_link()

                        if meet_link:
                            sql = (
                                "UPDATE calendar_event SET "
                                "videocall_location = %s, "
                                "google_meet_url = %s WHERE id = %s"
                            )
                            params = (meet_link, meet_link, event.id)
                            self.env.cr.execute(sql, params)
                            # Update the record in memory too
                            event.videocall_location = meet_link
                            event.google_meet_url = meet_link

                    except Exception:
                        pass
        return events

    def write(self, vals):
        """Override write to update Google Meet events when needed"""
        result = super().write(vals)

        if any(field in vals for field in ['start', 'stop', 'name']):
            for event in self:
                if (event.google_event_id and
                    event.booking_type_id and
                        event.booking_type_id._should_use_google_meet()):

                    try:
                        event._update_google_meet_event()
                    except Exception:
                        pass
        return result

    def clear_videocall_location(self):
        """Override to prevent clearing Google Meet URLs"""
        # Only clear if not using Google Meet
        for event in self:
            _logger.info(
                "clear_videocall_location called for event %s, "
                "videocall_location: %s",
                event.id, event.videocall_location
            )
            if (event.booking_type_id and
                    event.booking_type_id._should_use_google_meet() and
                    event.google_meet_url):
                _logger.info(
                    "Skipping clear for event %s - has Google Meet", event.id
                )
                continue
            else:
                _logger.info(
                    "Clearing videocall_location for event %s", event.id
                )
                super(CalendarEvent, event).clear_videocall_location()

    def _set_discuss_videocall_location(self):
        """Override to preserve Google Meet URLs"""
        for event in self:
            _logger.info(
                "_set_discuss_videocall_location called for event %s, "
                "current videocall_location: %s",
                event.id, event.videocall_location
            )
            if (event.booking_type_id and
                    event.booking_type_id._should_use_google_meet() and
                    event.google_meet_url):
                if event.videocall_location != event.google_meet_url:
                    _logger.info(
                        "Setting videocall_location to Google Meet URL: %s",
                        event.google_meet_url
                    )
                    event.videocall_location = event.google_meet_url
                else:
                    _logger.info(
                        "videocall_location already matches Google Meet URL"
                    )
            else:
                _logger.info(
                    "Using default _set_discuss_videocall_location "
                    "for event %s",
                    event.id
                )
                super(CalendarEvent, event)._set_discuss_videocall_location()

    def unlink(self):
        """Override unlink to delete Google Calendar events"""
        for event in self:
            if event.google_event_id:
                try:
                    event._delete_google_meet_event()
                except Exception:
                    pass

        return super().unlink()

    def _generate_google_meet_link(self):
        """Generate Google Meet link for this event"""
        _logger.info("Generating Google Meet link for event %s", self.id)

        if (not self.booking_type_id or
                not self.booking_type_id._should_use_google_meet()):
            _logger.info(
                "Event %s: No booking type or not using Google Meet", self.id
            )
            return False

        _logger.info("Getting Google Meet service")
        try:
            google_service = self.env['google.meet.service']
            _logger.info("Google Meet service obtained successfully")
        except KeyError as e:
            _logger.error("Google Meet service not found: %s", str(e))
            return False

        attendees = []
        for attendee in self.attendee_ids:
            if attendee.email and '@' in attendee.email:
                attendees.append(attendee.email)

        _logger.info("Found %d attendees: %s", len(attendees), attendees)

        description = self._format_meet_description()

        event_data = {
            'summary': self.name or 'Appointment',
            'description': description,
            'start_datetime': self.start.isoformat(),
            'end_datetime': self.stop.isoformat(),
            'timezone': 'UTC',
            'attendees': attendees,
        }

        _logger.info("Event data prepared: %s", event_data)

        try:
            _logger.info("Calling google_service.create_meet_event")
            result = google_service.create_meet_event(event_data)
            _logger.info("Google service result: %s", result)

            if result.get('success'):
                meet_link = result['meet_link']
                _logger.info("Successfully got Meet link: %s", meet_link)

                self.write({
                    'google_meet_url': meet_link,
                    'google_event_id': result['google_event_id'],
                    'google_meet_generated': True,
                    'meeting_url': meet_link,
                    'videocall_location': meet_link,
                })

                return meet_link
            else:
                _logger.error("Google service returned failure: %s", result)
                raise UserError(_("Failed to generate Google Meet link"))

        except Exception as e:
            _logger.error(
                "Exception in _generate_google_meet_link: %s", str(e)
            )
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
            'timezone': 'UTC',
        }

        result = google_service.update_meet_event(
            self.google_event_id,
            event_data
        )

        return result.get('success', False)

    def _delete_google_meet_event(self):
        """Delete Google Calendar event"""
        if not self.google_event_id:
            return False

        google_service = self.env['google.meet.service']
        result = google_service.delete_meet_event(self.google_event_id)

        return result.get('success', False)

    def _format_meet_description(self):
        """Format meeting description for Google Meet"""
        base_description = self.description or ""

        if self.booking_type_id:
            booking_name = self.booking_type_id.name or "Appointment"
            if booking_name not in base_description:
                base_description = f"{booking_name}\n\n{base_description}"

        if self.partner_ids:
            participants = ", ".join([
                p.name for p in self.partner_ids if p.name
            ])
            if participants:
                base_description = (
                    f"{base_description}\n\nParticipants: {participants}"
                )

        return base_description or f"Meeting: {self.name or 'Appointment'}"

    def _get_formatted_datetime(self):
        """Get safely formatted datetime for email templates"""
        if not self.start:
            return str(self.start or "")

        try:
            import pytz

            booking_tz = (
                self.booking_type_id.booking_tz if self.booking_type_id
                else 'Europe/Madrid'
            )
            booking_timezone = pytz.timezone(booking_tz)

            utc_timezone = pytz.timezone('UTC')
            utc_start = utc_timezone.localize(self.start)
            local_start = utc_start.astimezone(booking_timezone)

            return local_start.strftime("%d/%m/%Y %H:%M")
        except Exception:
            return str(self.start)

    def action_regenerate_google_meet(self):
        """Manual action to regenerate Google Meet link"""
        for event in self:
            if (not event.booking_type_id or
                    not event.booking_type_id._should_use_google_meet()):
                raise UserError(_(
                    "Google Meet is not enabled for this booking type"
                ))

            if event.google_event_id:
                event._delete_google_meet_event()

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
