# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class CalendarBookingType(models.Model):
    _inherit = 'calendar.booking.type'

    use_google_meet = fields.Boolean(
        string="Use Google Meet",
        default=True,
        help="Generate Google Meet links automatically for this booking type"
    )

    def _get_google_meet_config(self):
        """Check if Google Meet is properly configured"""
        try:
            config_model = self.env['res.config.settings'].sudo()
            config = config_model.get_google_meet_config()
            return (
                config.get('enabled') and
                config.get('client_id') and
                config.get('client_secret') and
                config.get('refresh_token')
            )
        except Exception:
            return False

    def _should_use_google_meet(self):
        """Check if this booking type should use Google Meet"""
        return (
            self.use_google_meet and
            self._get_google_meet_config()
        )
