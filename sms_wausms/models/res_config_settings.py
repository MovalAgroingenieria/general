# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, exceptions, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _description = 'Configuration of WauSMS'

    sms_service = fields.Selection(
        selection_add=[('wausms_service', 'WauSMS')])

    wausms_website = fields.Char(
        string='Website',
        default='dashboard.wausms.com',
        readonly=True)

    wausms_service_url = fields.Char(
        string='Service URL',
        default='https://dashboard.wausms.com/api/rest/message',
        config_parameter='sms_wausms.wausms_service_url')

    wausms_service_api_user = fields.Char(
        string='API User',
        config_parameter='sms_wausms.wausms_service_api_user')

    wausms_service_api_passwd = fields.Char(
        string='API Password',
        config_parameter='sms_wausms.wausms_service_api_passwd')

    wausms_service_sender = fields.Char(
        string='Sender',
        size=15,
        config_parameter='sms_wausms.wausms_service_sender')

    def set_values(self):
        super().set_values()
        param_obj = self.env['ir.config_parameter'].sudo()
        sender = param_obj.get_param(
            'sms_wausms.wausms_service_sender', default='')

        if sender and (sender.isdigit() and len(sender) > 15):
            raise exceptions.ValidationError(
                _('Sender size is limited to 15 numbers or 11 alphanumeric '
                  'characters.'))


