# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AssemblyAttendeeVote(models.Model):
    """Per (attendee, vote type): own / delegated in-out; total = own + in - out."""

    _name = "assembly.attendee.vote"
    _description = "Attendee vote by type"
    _order = "attendee_id, vote_type_id"

    attendee_id = fields.Many2one(
        "assembly.attendee",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="attendee_id.company_id",
        store=True,
        readonly=True,
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

    # DB-enforced: one row per (attendee, vote_type). Recompute upserts via
    # ``assembly.attendee._persist_attendee_vote_line`` (write-first); batch prefetch
    # uses ``assembly.attendee._collapse_duplicate_attendee_vote_lines``. Concurrent
    # inserts rely on UNIQUE + IntegrityError handling.
    _sql_constraints = [
        (
            "attendee_vote_type_uniq",
            "UNIQUE(attendee_id, vote_type_id)",
            "One vote record per type per attendee.",
        ),
        (
            "attendee_vote_own_non_negative",
            "CHECK(own_votes >= 0)",
            "Own votes cannot be negative.",
        ),
        (
            "attendee_vote_delegated_out_non_negative",
            "CHECK(delegated_out_votes >= 0)",
            "Delegated out votes cannot be negative.",
        ),
        (
            "attendee_vote_delegated_in_non_negative",
            "CHECK(delegated_in_votes >= 0)",
            "Delegated in votes cannot be negative.",
        ),
    ]

    @api.constrains("attendee_id", "vote_type_id")
    def _check_unique_vote_type_per_attendee(self):
        for record in self:
            if not record.attendee_id or not record.vote_type_id:
                continue
            domain = [
                ("attendee_id", "=", record.attendee_id.id),
                ("vote_type_id", "=", record.vote_type_id.id),
            ]
            if record.id:
                domain.append(("id", "!=", record.id))
            if self.search(domain, limit=1):
                raise ValidationError(
                    self.env._(
                        "Only one vote line per attendee and vote type is allowed."
                    )
                )

    @api.constrains("own_votes", "delegated_out_votes", "delegated_in_votes")
    def _check_votes_non_negative(self):
        for record in self:
            if record.own_votes < 0:
                raise ValidationError(
                    self.env._(
                        "Own votes cannot be negative. Current value: %(value)s",
                        value=record.own_votes,
                    )
                )
            if record.delegated_out_votes < 0:
                raise ValidationError(
                    self.env._(
                        "Delegated out votes cannot be negative. "
                        "Current value: %(value)s",
                        value=record.delegated_out_votes,
                    )
                )
            if record.delegated_in_votes < 0:
                raise ValidationError(
                    self.env._(
                        "Delegated in votes cannot be negative. "
                        "Current value: %(value)s",
                        value=record.delegated_in_votes,
                    )
                )

    @api.depends("own_votes", "delegated_out_votes", "delegated_in_votes")
    def _compute_attendee_vote_total(self):
        for record in self:
            record.attendee_vote_total = (
                record.own_votes
                + record.delegated_in_votes
                - record.delegated_out_votes
            )

    @api.model_create_multi
    def create(self, vals_list):
        att_ids = {v.get("attendee_id") for v in vals_list if v.get("attendee_id")}
        if att_ids:
            self.env["assembly.attendee"].browse(list(att_ids)).exists().mapped(
                "assembly_id"
            )._assembly_ensure_not_closed_for_related_changes()
        return super().create(vals_list)

    def write(self, vals):
        self.mapped(
            "attendee_id.assembly_id"
        )._assembly_ensure_not_closed_for_related_changes()
        return super().write(vals)

    def unlink(self):
        self.mapped(
            "attendee_id.assembly_id"
        )._assembly_ensure_not_closed_for_related_changes()
        return super().unlink()
