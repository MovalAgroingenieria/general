# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    def _default_fixed_concept(self):
        fixed_concept = False
        fixed_concept = self.env["account.move.fixedconcept"].search([
            ("default", "=", True)], limit=1)
        return fixed_concept

    invoice_fixed_concept_id = fields.Many2one(
        string="Fixed Concept",
        comodel_name="account.move.fixedconcept",
        default=_default_fixed_concept,
    )

    invoice_fixed_concept_has_extrafield = fields.Boolean(
        string="Has Extra Field",
        compute="_compute_invoice_fixed_concept_has_extrafield",
    )

    invoice_fixed_concept_extrafield = fields.Char(
        string="Extra Field",
    )

    @api.depends("invoice_fixed_concept_id")
    def _compute_invoice_fixed_concept_has_extrafield(self):
        for record in self:
            record.invoice_fixed_concept_has_extrafield = False
            if record.invoice_fixed_concept_id:
                record.invoice_fixed_concept_has_extrafield = \
                    record.invoice_fixed_concept_id.extra_field