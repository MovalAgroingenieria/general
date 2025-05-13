# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    _description = "Street type settings"

    street_type_shown = fields.Selection(
        [("not_show", "Not show"), ("short", "Abbreviation"), ("long", "Name")],
        string="Street type shown",
        config_parameter="partner_address_street_type.street_type_shown",
    )

    address_format_set = fields.Text(
        string="Address format",
        default=lambda self: self.env["res.country"]
        .search([("code", "=", self.env.company.country_id.code)], limit=1)
        .address_format,
    )

    def set_values(self):
        address_format_set = self.address_format_set
        company_country_code = (
            self.env["res.country"]
            .search([("code", "=", self.env.company.country_id.code)], limit=1)
            .code
        )
        query = f"""UPDATE res_country
            SET address_format = '{address_format_set}'
            WHERE code = '{company_country_code}';"""
        self.env.cr.execute(query)
        super().set_values()
