# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    _description = "Street type settings"

    street_type_shown = fields.Selection(
        [("not_show", "Not show"), ("short", "Abbreviation"), ("long", "Name")],
        string="Street type shown",
        required=True,
        default="long",
        config_parameter="partner_address_street_type.street_type_shown",
        help="Determine how the street type will be displayed.",
    )

    address_format_set = fields.Text(
        string="Address format",
        default=lambda self: self.env["res.country"]
        .search([("code", "=", self.env.company.country_id.code)], limit=1)
        .address_format,
        help="This field shows the current address format for company country.\
            You can change it with the python-style string pattern with all \
            address fields.\nThis format will be apply to company country.\n\
            Errors in the format are not detected.",
    )

    def open_street_types(self):
        action = self.env.ref(
            "partner_address_street_type.action_res_street_type_tree"
        ).read()[0]
        action["views"] = [
            [
                self.env.ref(
                    "partner_address_street_type.res_street_type_config_view_tree"
                ).id,
                "tree",
            ]
        ]
        return action

    def set_values(self):
        res = super().set_values()
        if self.address_format_set:
            company_country_code = (
                self.env["res.country"]
                .search([("code", "=", self.env.company.country_id.code)], limit=1)
                .code
            )
            new_format = self.address_format_set
            self.env.cr.execute(
                "UPDATE res_country SET address_format = %s WHERE code = %s",
                (new_format, company_country_code),
            )
        return res
