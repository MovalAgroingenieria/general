# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    street_type_id = fields.Many2one(
        string="Street type",
        comodel_name="res.street.type",
        ondelete="set null",
    )

    street_type_shown = fields.Char(
        string="Street type shown",
        compute="_compute_street_type_shown",
    )

    def _compute_street_type_shown(self):
        config_type_shown = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("partner_address_street_type.street_type_shown")
        )
        for record in self:
            street_type_shown = ""
            if record.street_type_id:
                if config_type_shown == "long":
                    street_type_shown = record.street_type_id.name
                elif config_type_shown == "short":
                    street_type_shown = record.street_type_id.abbreviation
                else:
                    street_type_shown = ""
            record.street_type_shown = street_type_shown

    @api.model
    def _address_fields(self):
        afields = super()._address_fields()
        afields.append("street_type_id")
        afields.append("street_type_shown")
        return afields

    @api.model_create_multi
    def create(self, vals):
        if "street_type_id" in vals:
            config_type_shown = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("partner_address_street_type.street_type_shown")
            )
            street_type_id = vals.get("street_type_id")
            street_type = self.env["res.street.type"].browse(street_type_id)
            if config_type_shown == "long":
                vals["street_type_shown"] = street_type.name
            elif config_type_shown == "short":
                vals["street_type_shown"] = street_type.abbreviation
            else:
                vals["street_type_shown"] = ""
        return super().create(vals)

    def write(self, vals):
        if "street_type_id" in vals:
            config_type_shown = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("partner_address_street_type.street_type_shown")
            )
            street_type_id = vals.get("street_type_id")
            street_type = self.env["res.street.type"].browse(street_type_id)
            if config_type_shown == "long":
                vals.update({"street_type_shown": street_type.name})
            elif config_type_shown == "short":
                vals.update({"street_type_shown": street_type.abbreviation})
            else:
                vals.update({"street_type_shown": ""})
        return super().write(vals)
