# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class AssemblyVoting(models.Model):
    _name = "assembly.voting"
    _inherit = ["assembly.mixin.open.assembly"]
    _description = "Assembly voting"
    _order = "agenda_id, date_open desc"

    agenda_id = fields.Many2one(
        "assembly.agenda",
        string="Agenda item",
        required=True,
        ondelete="cascade",
        index=True,
    )
    assembly_id = fields.Many2one(
        "assembly.assembly",
        related="agenda_id.assembly_id",
        store=True,
        readonly=True,
    )
    vote_type_id = fields.Many2one(
        "vote.type",
        string="Vote type",
        required=True,
        ondelete="restrict",
    )
    name = fields.Char(string="Description", default="/")
    voting_state = fields.Selection(
        [("open", "Open"), ("closed", "Closed"), ("cancelled", "Cancelled")],
        string="State",
        default="open",
        required=True,
    )
    date_open = fields.Datetime(string="Opened at")
    date_close = fields.Datetime(string="Closed at")
    vote_line_ids = fields.One2many(
        "assembly.voting.line",
        "voting_id",
        string="Votes cast",
    )
    result_ids = fields.One2many(
        "assembly.voting.result",
        "voting_id",
        string="Results",
    )
    total_votes_cast = fields.Float(
        compute="_compute_totals",
        store=True,
    )
    total_votes_possible = fields.Float(
        compute="_compute_totals",
        store=True,
    )
    participation_percentage = fields.Float(
        compute="_compute_totals",
        store=True,
    )
    count_vote_lines = fields.Integer(
        string="Vote lines",
        compute="_compute_count_lines_results",
    )
    count_results = fields.Integer(
        string="Results count",
        compute="_compute_count_lines_results",
    )

    @api.depends("vote_line_ids", "result_ids")
    def _compute_count_lines_results(self):
        for rec in self:
            rec.count_vote_lines = len(rec.vote_line_ids)
            rec.count_results = len(rec.result_ids)

    def action_open_agenda_item(self):
        return self._action_window(
            "assembly.agenda",
            self.env._("Agenda item"),
            "form",
            res_id=self.agenda_id.id,
        )

    def action_open_vote_lines(self):
        return self._action_window(
            "assembly.voting.line",
            self.env._("Votes cast"),
            "list,form",
            domain=[("voting_id", "=", self.id)],
            context={"default_voting_id": self.id},
        )

    def action_open_results(self):
        return self._action_window(
            "assembly.voting.result",
            self.env._("Results"),
            "list,form",
            domain=[("voting_id", "=", self.id)],
            context={"default_voting_id": self.id},
        )

    @api.constrains("name")
    def _check_name_non_empty(self):
        for rec in self:
            if not (rec.name or "").strip():
                raise ValidationError(self.env._("Voting description cannot be empty."))

    @api.constrains("vote_type_id", "agenda_id")
    def _check_vote_type_consistent_with_agenda(self):
        for rec in self:
            if not rec.agenda_id or not rec.vote_type_id:
                continue
            assembly = rec.agenda_id.assembly_id
            if not assembly:
                continue
            avt = assembly.vote_type_ids
            if rec.vote_type_id not in avt:
                raise ValidationError(
                    self.env._(
                        "The voting vote type must be one of the assembly's vote types."
                    )
                )
            if (
                rec.agenda_id.requires_vote
                and rec.agenda_id.vote_type_id
                and rec.vote_type_id != rec.agenda_id.vote_type_id
            ):
                raise ValidationError(
                    self.env._(
                        "The voting vote type must match the agenda item's vote type."
                    )
                )

    @api.model
    def _apply_default_name_to_voting_create_vals(self, vals_list):
        for vals in vals_list:
            if vals.get("name"):
                continue
            if vals.get("agenda_id"):
                agenda = self.env["assembly.agenda"].browse(vals["agenda_id"])
                if agenda.exists():
                    vals["name"] = agenda.name or "/"
            if not vals.get("name"):
                vals["name"] = "/"

    @api.model_create_multi
    def create(self, vals_list):
        self._apply_default_name_to_voting_create_vals(vals_list)
        return super().create(vals_list)

    @api.depends(
        "vote_line_ids", "vote_line_ids.votes_applied", "agenda_id", "vote_type_id"
    )
    def _compute_totals(self):
        Attendee = self.env["assembly.attendee"]
        AttendeeVote = self.env["assembly.attendee.vote"]
        for voting in self:
            total_cast = sum(voting.vote_line_ids.mapped("votes_applied"))
            possible = 0.0
            if voting.agenda_id and voting.vote_type_id:
                attendees = Attendee._search_attendees_for_assembly(
                    voting.assembly_id.id,
                    attendee_state="confirmed",
                )
                if attendees:
                    lines = AttendeeVote.search(
                        [
                            ("attendee_id", "in", attendees.ids),
                            ("vote_type_id", "=", voting.vote_type_id.id),
                        ]
                    )
                    possible = sum(lines.mapped("attendee_vote_total"))
            voting.total_votes_cast = total_cast
            voting.total_votes_possible = possible
            voting.participation_percentage = (
                (total_cast / possible * 100.0) if possible else 0.0
            )

    def action_close(self):
        for rec in self:
            if rec.voting_state != "open":
                raise UserError(self.env._("Only open votings can be closed."))
            rec.write(
                {
                    "voting_state": "closed",
                    "date_close": fields.Datetime.now(),
                }
            )
            rec._persist_closed_voting_results()  # pylint: disable=protected-access
            rec.agenda_id.write({"agenda_state": "voted"})

    def action_cancel(self):
        for rec in self:
            if rec.voting_state != "open":
                raise UserError(self.env._("Only open votings can be cancelled."))
            rec.write({"voting_state": "cancelled"})

    def _persist_closed_voting_results(self):
        self.ensure_one()
        result_model = self.env["assembly.voting.result"]
        possible = self.total_votes_possible
        cast = self.total_votes_cast
        for option in ["yes", "no", "abstention", "blank"]:
            lines_for_option = self.vote_line_ids.filtered(
                lambda line, opt=option, option=option: line.vote_option == opt
            )
            total = sum(lines_for_option.mapped("votes_applied"))
            pct = (total / possible * 100.0) if possible else 0.0
            result_model.create(
                {
                    "voting_id": self.id,
                    "vote_option": option,
                    "total_votes": total,
                    "result_percentage": pct,
                }
            )
        not_cast = possible - cast
        pct_nc = (not_cast / possible * 100.0) if possible else 0.0
        result_model.create(
            {
                "voting_id": self.id,
                "vote_option": "not_cast",
                "total_votes": not_cast,
                "result_percentage": pct_nc,
            }
        )
