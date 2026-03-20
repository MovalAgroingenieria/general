# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class AssemblyDelegation(models.Model):
    _name = "assembly.delegation"
    _description = "Vote delegation"
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
        string="Delegator",
        required=True,
        ondelete="cascade",
        index=True,
    )
    delegate_partner_id = fields.Many2one(
        "res.partner",
        string="Delegate",
        required=True,
        ondelete="cascade",
        index=True,
    )
    vote_type_ids = fields.Many2many(
        "vote.type",
        "assembly_delegation_vote_type_rel",
        "delegation_id",
        "vote_type_id",
        string="Vote types",
        domain="[('active', '=', True)]",
        help="Leave empty to delegate all vote types.",
    )
    date_delegation = fields.Datetime(default=fields.Datetime.now)
    delegation_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("revoked", "Revoked"),
        ],
        string="State",
        default="draft",
        required=True,
    )

    @api.constrains("partner_id", "delegate_partner_id")
    def _check_not_self(self):
        for rec in self:
            if rec.partner_id == rec.delegate_partner_id:
                raise ValidationError(
                    self.env._("Delegator and delegate must be different.")
                )

    @api.constrains("delegate_partner_id", "assembly_id")
    def _check_delegate_convocable(self):
        for rec in self:
            try:
                domain = safe_eval(
                    rec.assembly_id.partner_domain or "[]", {"__builtins__": {}}
                )
            except (TypeError, ValueError, SyntaxError, MemoryError):
                domain = []
            partners = self.env["res.partner"].search(domain)
            if rec.delegate_partner_id not in partners:
                raise ValidationError(
                    self.env._("The delegate must be in the convocable partners list.")
                )

    @api.constrains("vote_type_ids", "assembly_id")
    def _check_vote_types_in_assembly(self):
        for rec in self:
            if rec.vote_type_ids and rec.assembly_id and rec.assembly_id.vote_type_ids:
                invalid = rec.vote_type_ids - rec.assembly_id.vote_type_ids
                if invalid:
                    raise ValidationError(
                        self.env._(
                            "Vote types must be among the assembly's vote types."
                        )
                    )

    @api.constrains("partner_id", "assembly_id", "vote_type_ids", "delegation_state")
    def _check_no_duplicate_confirmed_delegation_per_type(self):
        """No two confirmed delegations for same partner covering same vote type."""
        for rec in self:
            if rec.delegation_state != "confirmed":
                continue
            effective_types = rec.vote_type_ids or rec.assembly_id.vote_type_ids
            other = self.search(
                [
                    ("id", "!=", rec.id),
                    ("assembly_id", "=", rec.assembly_id.id),
                    ("partner_id", "=", rec.partner_id.id),
                    ("delegation_state", "=", "confirmed"),
                ]
            )
            for other_rec in other:
                other_effective = (
                    other_rec.vote_type_ids or other_rec.assembly_id.vote_type_ids
                )
                overlap = effective_types & other_effective
                if overlap:
                    raise ValidationError(
                        self.env._(
                            "You already have a confirmed delegation in this "
                            "assembly that covers the same vote type(s). "
                            "Revoke or edit the other delegation first."
                        )
                    )

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

    def write(self, vals):
        res = super().write(vals)
        if "delegation_state" in vals and vals["delegation_state"] in (
            "confirmed",
            "revoked",
        ):
            for rec in self:
                attendees = self.env["assembly.attendee"].search(
                    [
                        ("assembly_id", "=", rec.assembly_id.id),
                        (
                            "partner_id",
                            "in",
                            (rec.partner_id.id, rec.delegate_partner_id.id),
                        ),
                    ]
                )
                attendees.recompute_votes()
        return res
