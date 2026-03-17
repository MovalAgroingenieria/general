# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class PartnerVote(models.Model):
    _name = "partner.vote"
    _description = "Partner Vote"
    _order = "partner_id, vote_type_id"

    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required=True,
        ondelete="cascade",
        index=True,
    )
    vote_type_id = fields.Many2one(
        "vote.type",
        string="Vote type",
        required=True,
        ondelete="cascade",
        index=True,
    )
    vote_count_integer = fields.Integer(string="Votes (integer)", default=0)
    vote_count_float = fields.Float(string="Votes (decimal)", default=0.0)
    vote_count_display = fields.Float(
        string="Votes",
        compute="_compute_vote_count_display",
        store=False,
        readonly=True,
    )
    last_compute_date = fields.Datetime(string="Last computed", readonly=True)
    formula_detail = fields.Text(string="Formula detail", readonly=True)

    _sql_constraints = [
        (
            "partner_vote_type_uniq",
            "UNIQUE(partner_id, vote_type_id)",
            "A partner can only have one vote record per vote type.",
        ),
    ]

    @api.depends(
        "vote_type_id",
        "vote_type_id.vote_value_type",
        "vote_count_integer",
        "vote_count_float",
    )
    def _compute_vote_count_display(self):
        for rec in self:
            if rec.vote_type_id.vote_value_type == "integer":
                rec.vote_count_display = float(rec.vote_count_integer)
            else:
                rec.vote_count_display = rec.vote_count_float
