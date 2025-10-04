# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    google_meet_enabled = fields.Boolean(
        string="Enable Google Meet Integration",
        config_parameter='google_meet.enabled',
        help="Enable automatic Google Meet link generation for appointments"
    )
    google_meet_client_id = fields.Char(
        string="Google Client ID",
        config_parameter='google_meet.client_id',
        help="Google OAuth Client ID for API access"
    )
    google_meet_client_secret = fields.Char(
        string="Google Client Secret",
        config_parameter='google_meet.client_secret',
        help="Google OAuth Client Secret for API access"
    )
    google_meet_account_email = fields.Char(
        string="Google Account Email",
        config_parameter='google_meet.account_email',
        help="Email of the Google account that will host the meetings"
    )
    google_meet_refresh_token = fields.Char(
        string="Google Refresh Token",
        config_parameter='google_meet.refresh_token',
        help="OAuth Refresh Token (auto-generated after authorization)"
    )
    google_meet_calendar_id = fields.Char(
        string="Google Calendar ID",
        config_parameter='google_meet.calendar_id',
        default='primary',
        help="Google Calendar ID for events (primary by default)"
    )

    def action_google_meet_authorize(self):
        """Redirect to Google OAuth authorization flow"""
        self.ensure_one()

        if not self.google_meet_client_id:
            raise UserError(_("Please configure Google Client ID first."))
        if not self.google_meet_client_secret:
            raise UserError(_("Please configure Google Client Secret first."))

        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url'
        )
        redirect_uri = "{}/google_meet_authentication".format(base_url)

        client_id = self.google_meet_client_id
        scope = "https://www.googleapis.com/auth/calendar"

        auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = [
            "response_type=code",
            "access_type=offline",
            "client_id={}".format(client_id),
            "redirect_uri={}".format(redirect_uri),
            "scope={}".format(scope),
            "prompt=consent"
        ]

        final_url = "{}?{}".format(auth_url, "&".join(params))

        return {
            'type': 'ir.actions.act_url',
            'url': final_url,
            'target': 'new'
        }

    def action_google_meet_test_connection(self):
        """Test Google Meet API connection"""
        if not self.google_meet_refresh_token:
            raise UserError(_(
                "Please authorize Google Meet integration first."
            ))

        if (self.google_meet_client_id and
                self.google_meet_client_secret and
                self.google_meet_refresh_token):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Success!"),
                    'message': _(
                        "Google Meet configuration is complete."
                    ),
                    'type': 'success',
                }
            }
        else:
            raise UserError(_(
                "Google Meet configuration is incomplete."
            ))

    @api.model
    def get_google_meet_config(self):
        """Get Google Meet configuration parameters"""
        return {
            'enabled': self.env['ir.config_parameter'].sudo().get_param(
                'google_meet.enabled', default=False
            ),
            'client_id': self.env['ir.config_parameter'].sudo().get_param(
                'google_meet.client_id'
            ),
            'client_secret': self.env['ir.config_parameter'].sudo().get_param(
                'google_meet.client_secret'
            ),
            'account_email': self.env['ir.config_parameter'].sudo().get_param(
                'google_meet.account_email'
            ),
            'refresh_token': self.env['ir.config_parameter'].sudo().get_param(
                'google_meet.refresh_token'
            ),
            'calendar_id': self.env['ir.config_parameter'].sudo().get_param(
                'google_meet.calendar_id', default='primary'
            ),
        }
