# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class CalendarBookingType(models.Model):
    _inherit = 'calendar.booking.type'

    # Google Meet Configuration per booking type
    use_google_meet = fields.Boolean(
        string="Use Google Meet",
        default=True,
        help="Generate Google Meet links automatically for this booking type"
    )
    google_meet_auto_record = fields.Boolean(
        string="Auto Record with TLDV",
        default=True,
        help="Enable automatic recording via TLDV integration"
    )
    google_meet_description_template = fields.Text(
        string="Meeting Description Template",
        default="""Appointment: {name}
Client: {partner_name}
Date: {start_date}
Duration: {duration} hours

Join the meeting: {meet_link}
        """,
        help="Template for Google Meet event description. "
             "Available placeholders: {name}, {partner_name}, "
             "{start_date}, {duration}, {meet_link}"
    )

    @api.onchange('use_google_meet')
    def _onchange_use_google_meet(self):
        """Clear meeting_base_url when Google Meet is enabled"""
        if self.use_google_meet:
            # Clear the base URL to let Google Meet take precedence
            self.meeting_base_url = False

    def _get_google_meet_config(self):
        """Check if Google Meet is properly configured"""
        config = self.env['res.config.settings'].get_google_meet_config()
        return (
            config.get('enabled') and
            config.get('client_id') and
            config.get('client_secret') and
            config.get('refresh_token')
        )

    def _should_use_google_meet(self):
        """Check if this booking type should use Google Meet"""
        return (
            self.use_google_meet and
            self._get_google_meet_config()
        )