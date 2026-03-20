# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AssemblyAttendeeVote(models.Model):
    _name = "assembly.attendee.vote"
    _description = "Attendee vote by type"
    _order = "attendee_id, vote_type_id"

    attendee_id = fields.Many2one(
        "assembly.attendee",
        string="Attendee",
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
    own_votes = fields.Float(string="Own votes", default=0.0)
    delegated_out_votes = fields.Float(string="Delegated out", default=0.0)
    delegated_in_votes = fields.Float(string="Delegated in", default=0.0)
    attendee_vote_total = fields.Float(
        string="Total",
        compute="_compute_attendee_vote_total",
        store=True,
    )

    _sql_constraints = [
        (
            "attendee_vote_type_uniq",
            "UNIQUE(attendee_id, vote_type_id)",
            "One vote record per type per attendee.",
        ),
    ]

    @api.depends("own_votes", "delegated_out_votes", "delegated_in_votes")
    def _compute_attendee_vote_total(self):
        for rec in self:
            rec.attendee_vote_total = (
                rec.own_votes - rec.delegated_out_votes + rec.delegated_in_votes
            )
