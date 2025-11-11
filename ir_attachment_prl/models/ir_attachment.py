# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    state = fields.Selection(
        [("red", "Red"), ("green", "Green")],
        string="Status",
        compute="_compute_state",
        store=False,  # store not needed; set to True if
        # you want to filter/search by this field
    )
    contracting_company_id = fields.Many2one("res.partner", copy=False)
    document_type = fields.Selection(
        [
            ("admin", "Administrative"),
            ("worker", "Worker"),
            ("machinery", "Machinery"),
            ("supplier_form", "Supplier Form"),
            ("technical_details", "Technical Details"),
            ("safety_details", "Safety Details"),
            ("analysis", "Analysis"),
            ("declaration_conformity", "Declaration of Conformity"),
            ("declaration_manger", "Declaration Manager"),
            ("quality_certificate", "Quality Certificate"),
            ("health_registration", "Health Registration"),
            ("appcc", "APPCC"),
            ("contract", "Contract"),
            ("migration_test", "Migration Test"),
        ],
        copy=False,
    )
    worker_id = fields.Many2one("res.partner", string="Worker", copy=False)
    machinery = fields.Text(copy=False)
    revision = fields.Selection(
        [("to_review", "To Review"), ("reviewed", "Reviewed")],
        copy=False,
    )
    date_request = fields.Date(string="Request Date", copy=False)
    expiration_date = fields.Date(copy=False)
    is_prl = fields.Boolean(string="Is PRL", default=False, copy=False)

    @api.depends("expiration_date")
    def _compute_state(self):
        """Red if expired (expiration_date <= today), otherwise green."""
        today = fields.Date.context_today(self)
        for rec in self:
            # If you want the previous logic (red with future date), use:
            # `rec.expiration_date and rec.expiration_date > today`
            rec.state = (
                "red"
                if rec.expiration_date and rec.expiration_date <= today
                else "green"
            )

    @api.model_create_multi
    def create(self, vals_list):
        """
        - Respects context shortcuts you already had.
        - For PRL, assigns the attachment to the partner
        (worker or contracting company).
        - Corrects 'res.model' -> 'res_model'.
        - Does not write 'res_name' (in v18 it's computed).
        """
        ctx = self.env.context

        # Accept dict or list
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        # If we don't come from PRL flow and there's no default, delegate
        if not ctx.get("active_model") and not ctx.get("default_is_prl"):
            return super().create(vals_list)

        # Specific case: account.journal -> don't modify
        if ctx.get("active_model") == "account.journal":
            return super().create(vals_list)

        # Specific case: account.analytic.line -> clear res_model=partner if it appears
        if ctx.get("active_model") == "account.analytic.line":
            for vals in vals_list:
                if vals.get("res_model") == "res.partner":
                    vals.pop("res_model", None)
            return super().create(vals_list)

        # PRL flow: assign to appropriate partner
        for vals in vals_list:
            if vals.get("is_prl"):
                partner_id = None
                if vals.get("document_type") == "worker" and vals.get("worker_id"):
                    partner_id = vals.get("worker_id")
                else:
                    partner_id = vals.get("contracting_company_id")

                if partner_id:
                    # Ensures link to partner
                    vals.update(
                        {
                            "res_model": "res.partner",
                            "res_id": partner_id,
                        }
                    )
                    # 'res_name' is computed; don't force it

        return super().create(vals_list)
