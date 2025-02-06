# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, tools


class DecimalPrecision(models.Model):
    _inherit = 'decimal.precision'

    display_digits = fields.Integer(
        string='Display Digits',
        required=True,)

    @api.model
    def create(self, vals):
        if 'digits' in vals and 'display_digits' not in vals:
            vals['display_digits'] = vals['digits']
        return super(DecimalPrecision, self).create(vals)

    @staticmethod
    # @tools.ormcache('application') Add in case of performace issues 15/2/2024
    def get_display_precision(env, application):
        res = 2
        dp = env['decimal.precision']
        dp.flush(['name', 'digits'])
        dp.env.cr.execute(
            'SELECT display_digits FROM decimal_precision WHERE name=%s',
            (application,))
        res = dp.env.cr.fetchone()
        res = res[0] if res else 2
        return 16, res
