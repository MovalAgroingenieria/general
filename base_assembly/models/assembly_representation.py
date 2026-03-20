# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class AssemblyRepresentation(models.Model):
    _name = "assembly.representation"
    _description = "Legal representation (partner represented by agent)"
    _order = "assembly_id, partner_id"

    assembly_id = fields.Many2one(
        "assembly.assembly",
        string="Assembly",
        required=True,
        ondelete="cascade",
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Represented (principal)",
        required=True,
        ondelete="cascade",
        index=True,
        help="Partner who designates a representative.",
    )
    agent_id = fields.Many2one(
        "res.partner",
        string="Representative (agent)",
        required=True,
        ondelete="cascade",
        index=True,
        help="Partner who attends and votes on behalf of the principal.",
    )
    representation_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("revoked", "Revoked"),
        ],
        string="State",
        default="draft",
        required=True,
    )
    date_representation = fields.Datetime(default=fields.Datetime.now)

    def action_open_assembly(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Assembly"),
            "res_model": "assembly.assembly",
            "view_mode": "form",
            "res_id": self.assembly_id.id,
            "target": "current",
        }

    @api.constrains("partner_id", "agent_id")
    def _check_not_self(self):
        for rec in self:
            if rec.partner_id == rec.agent_id:
                raise ValidationError(
                    rec.env._("Represented and representative must be different.")
                )

    @api.constrains("agent_id", "assembly_id")
    def _check_agent_convocable(self):
        for rec in self:
            try:
                domain = safe_eval(
                    rec.assembly_id.partner_domain or "[]", {"__builtins__": {}}
                )
            except (TypeError, ValueError, SyntaxError, MemoryError):
                domain = []
            partners = self.env["res.partner"].search(domain)
            if rec.agent_id not in partners:
                raise ValidationError(
                    rec.env._(
                        "The representative must be in the convocable partners list."
                    )
                )
