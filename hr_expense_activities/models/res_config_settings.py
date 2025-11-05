
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    with_activity = fields.Boolean(
        string='Create new activity for new expense',
        default=False,
        config_parameter = 'ht_expense_activities.with_activity'
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res['with_activity'] = self.env['ir.config_parameter'].\
            sudo().get_param(
                'hr_expense_activities.with_activity',
                default=False)
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'hr_expense_activities.with_activity',
            self.with_activity)
