# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AssemblyVotingLine(models.Model):
    _name = "assembly.voting.line"
    _description = "Voting line (cast vote)"

    voting_id = fields.Many2one(
        "assembly.voting",
        string="Voting",
        required=True,
        ondelete="cascade",
        index=True,
    )
    attendee_id = fields.Many2one(
        "assembly.attendee",
        string="Attendee",
        required=True,
        ondelete="cascade",
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        related="attendee_id.partner_id",
        store=True,
        readonly=True,
    )
    vote_option = fields.Selection(
        [
            ("yes", "Yes"),
            ("no", "No"),
            ("abstention", "Abstention"),
            ("blank", "Blank"),
        ],
        string="Vote",
        required=True,
    )
    votes_applied = fields.Float(
        string="Votes applied",
        required=True,
        help="Frozen from attendee vote total at cast time.",
    )
    vote_channel = fields.Selection(
        [
            ("in_person", "In person"),
            ("online", "Online"),
        ],
        string="Channel",
        default="in_person",
        required=True,
        help="How the vote was cast: in person or online.",
    )
    vote_cast_at = fields.Datetime(
        string="Cast at",
        help="Server timestamp when the vote was recorded.",
    )
    vote_cast_by_user_id = fields.Many2one(
        "res.users",
        string="Cast by user",
        ondelete="set null",
        help="User who cast the vote (portal/backend). Empty if cast via token.",
    )

    _sql_constraints = [
        (
            "voting_attendee_uniq",
            "UNIQUE(voting_id, attendee_id)",
            "Each attendee can vote only once per voting.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        for vals in vals_list:
            if "vote_cast_at" not in vals:
                vals["vote_cast_at"] = now
            if (
                "vote_cast_by_user_id" not in vals
                and self.env.user
                and self.env.user.id
            ):
                vals["vote_cast_by_user_id"] = self.env.uid
        return super().create(vals_list)

    @api.constrains("votes_applied")
    def _check_votes_applied_non_negative(self):
        for line in self:
            if line.votes_applied < 0:
                raise ValidationError(self.env._("Votes applied cannot be negative."))

    @api.constrains("voting_id")
    def _check_voting_open(self):
        for line in self:
            if line.voting_id.voting_state != "open":
                raise ValidationError(
                    self.env._(
                        "A vote line can only be created when the voting is open."
                    )
                )

    @api.onchange("attendee_id")
    def _onchange_attendee_id(self):
        if self.attendee_id and self.voting_id and self.voting_id.vote_type_id:
            vote_type = self.voting_id.vote_type_id
            av = self.attendee_id.attendee_vote_ids.filtered(
                lambda v, vt=vote_type: v.vote_type_id == vt
            )
            if av:
                self.votes_applied = av.attendee_vote_total
            else:
                self.votes_applied = 0.0

    @api.constrains("attendee_id", "voting_id", "votes_applied")
    def _check_can_vote(self):
        for line in self:
            vote_type = line.voting_id.vote_type_id
            av = line.attendee_id.attendee_vote_ids.filtered(
                lambda v, vt=vote_type: v.vote_type_id == vt
            )
            if not av or av.attendee_vote_total <= 0:
                raise ValidationError(
                    self.env._(
                        "This attendee has no votes for this vote type (delegated out)."
                    )
                )
            if line.votes_applied != av.attendee_vote_total:
                raise ValidationError(
                    self.env._(
                        "Votes applied must match the attendee's vote total for "
                        "this type."
                    )
                )
