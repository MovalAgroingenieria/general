# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class FileConfiguration(models.TransientModel):
    _inherit = 'res.config.settings'
    _description = 'Configuration of File Management'

    file_prefix = fields.Char(
        string='File Prefix',
        config_parameter='crm_filemgmt.file_prefix',
        help='Company-dependent prefix for Files. Maximum 10 characters.')

    @api.model
    def get_values(self):
        res = super().get_values()
        company_id = str(self.env.company.id)
        param_key = f'crm_filemgmt.file_prefix_{company_id}'
        res['file_prefix'] = self.env['ir.config_parameter'].sudo(
            ).get_param(param_key, default='')
        return res

    def set_values(self):
        super().set_values()
        company_id = str(self.env.company.id)
        param_key = f'crm_filemgmt.file_prefix_{company_id}'
        self.env['ir.config_parameter'].sudo().set_param(
            param_key, self.file_prefix)
