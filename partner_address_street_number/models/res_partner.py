# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    street_num = fields.Char(
        string="Street number"
    )

    @api.model
    def _address_fields(self):
        fields = super(ResPartner, self)._address_fields()
        fields.append('street_num')
        return fields
