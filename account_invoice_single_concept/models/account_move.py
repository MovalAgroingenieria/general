# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    def _default_single_concept(self):
        single_concept = False
        single_concept = self.env["account.move.singleconcept"].search([
            ("default", "=", True)], limit=1)
        return single_concept

    invoice_single_concept_id = fields.Many2one(
        string="Single Concept",
        comodel_name="account.move.singleconcept",
        default=_default_single_concept,
    )

    invoice_single_concept_has_extrafield = fields.Boolean(
        string="Has Extra Field",
        compute="_compute_invoice_single_concept_has_extrafield",
    )

    invoice_single_concept_extrafield = fields.Char(
        string="Extra Field",
    )

    @api.depends("invoice_single_concept_id")
    def _compute_invoice_single_concept_has_extrafield(self):
        for record in self:
            record.invoice_single_concept_has_extrafield = False
            if record.invoice_single_concept_id:
                record.invoice_single_concept_has_extrafield = \
                    record.invoice_single_concept_id.extra_field