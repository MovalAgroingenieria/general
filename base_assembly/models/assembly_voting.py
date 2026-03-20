# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import UserError


class AssemblyVoting(models.Model):
    _name = "assembly.voting"
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
    name = fields.Char(string="Description")
    voting_state = fields.Selection(
        [("open", "Open"), ("closed", "Closed"), ("cancelled", "Cancelled")],
        string="State",
        default="open",
        required=True,
    )
    date_open = fields.Datetime(string="Opened at")
    date_close = fields.Datetime(string="Closed at")
    allow_online_voting = fields.Boolean(
        string="Allow online voting",
        related="assembly_id.allow_online_voting",
        readonly=True,
    )
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

    def action_open_agenda_item(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Agenda item"),
            "res_model": "assembly.agenda",
            "view_mode": "form",
            "res_id": self.agenda_id.id,
            "target": "current",
        }

    def action_open_vote_lines(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Votes cast"),
            "res_model": "assembly.voting.line",
            "view_mode": "list,form",
            "domain": [("voting_id", "=", self.id)],
            "context": {"default_voting_id": self.id},
        }

    def action_open_results(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Results"),
            "res_model": "assembly.voting.result",
            "view_mode": "list,form",
            "domain": [("voting_id", "=", self.id)],
            "context": {"default_voting_id": self.id},
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") and vals.get("agenda_id"):
                agenda = self.env["assembly.agenda"].browse(vals["agenda_id"])
                if agenda.exists():
                    vals["name"] = agenda.name
        return super().create(vals_list)

    @api.depends(
        "vote_line_ids", "vote_line_ids.votes_applied", "agenda_id", "vote_type_id"
    )
    def _compute_totals(self):
        for voting in self:
            total_cast = sum(voting.vote_line_ids.mapped("votes_applied"))
            possible = 0.0
            if voting.agenda_id and voting.vote_type_id:
                attendees = self.env["assembly.attendee"].search(
                    [
                        ("assembly_id", "=", voting.assembly_id.id),
                        ("attendee_state", "=", "confirmed"),
                    ]
                )
                for att in attendees:
                    avs = att.attendee_vote_ids
                    av = next(
                        (x for x in avs if x.vote_type_id == voting.vote_type_id),
                        None,
                    )
                    if av:
                        possible += av.attendee_vote_total
            voting.total_votes_cast = total_cast
            voting.total_votes_possible = possible
            voting.participation_percentage = (
                (total_cast / possible * 100.0) if possible else 0.0
            )

    def action_close(self):
        for rec in self:
            if rec.voting_state != "open":
                raise UserError(self.env._("Only open votings can be closed."))
            rec.voting_state = "closed"
            rec.date_close = fields.Datetime.now()
            rec._create_results()  # pylint: disable=protected-access
            rec.agenda_id.agenda_state = "voted"

    def action_cancel(self):
        for rec in self:
            if rec.voting_state != "open":
                raise UserError(self.env._("Only open votings can be cancelled."))
            rec.voting_state = "cancelled"

    def _create_results(self):
        self.ensure_one()
        result_model = self.env["assembly.voting.result"]
        possible = self.total_votes_possible
        cast = self.total_votes_cast
        for option in ["yes", "no", "abstention", "blank"]:
            lines_for_option = self.vote_line_ids.filtered(
                lambda line, opt=option: line.vote_option == opt
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
