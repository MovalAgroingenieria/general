# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    partner_vote_ids = fields.One2many(
        "partner.vote",
        "partner_id",
        string="Votes",
        domain=[("vote_type_id.active", "=", True)],
    )
    total_votes_display = fields.Float(
        string="Total votes (informative)",
        compute="_compute_total_votes_display",
        store=False,
        help="Sum of vote_count_display for active vote types. Informative only.",
    )

    @api.depends(
        "partner_vote_ids",
        "partner_vote_ids.vote_count_display",
        "partner_vote_ids.vote_type_id",
    )
    def _compute_total_votes_display(self):
        for partner in self:
            total = 0.0
            for pv in partner.partner_vote_ids.filtered(
                lambda v: v.vote_type_id.active
            ):
                total += pv.vote_count_display
            partner.total_votes_display = total

    def action_recompute_my_votes(self):
        self.ensure_one()
        active_types = self.env["vote.type"].search([("active", "=", True)])
        partner_vote_model = self.env["partner.vote"]
        for vote_type in active_types:
            partners = vote_type._get_partners_to_compute()
            vote = partner_vote_model.search(
                [
                    ("partner_id", "=", self.id),
                    ("vote_type_id", "=", vote_type.id),
                ],
                limit=1,
            )
            if self not in partners:
                if vote:
                    vote.unlink()
                continue
            value, detail = vote_type.evaluate_formula(self)
            now = fields.Datetime.now()
            if vote_type.vote_value_type == "integer":
                vals = {
                    "vote_count_integer": int(value),
                    "vote_count_float": 0.0,
                    "last_compute_date": now,
                    "formula_detail": detail,
                }
            else:
                vals = {
                    "vote_count_integer": 0,
                    "vote_count_float": value,
                    "last_compute_date": now,
                    "formula_detail": detail,
                }
            if vote:
                vote.write(vals)
            else:
                partner_vote_model.create(
                    {
                        "partner_id": self.id,
                        "vote_type_id": vote_type.id,
                        **vals,
                    }
                )
        return True
