# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sms_service = fields.Selection([
        ('odoo_service', 'Odoo')],
        string='SMS Service',
        default='odoo_service',
        config_parameter='sms_alternatives.sms_service',
        help='The SMS service to be used.')
