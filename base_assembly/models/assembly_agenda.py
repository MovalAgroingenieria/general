# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AssemblyAgenda(models.Model):
    _name = "assembly.agenda"
    _description = "Assembly agenda item"
    _order = "assembly_id, sequence, id"

    assembly_id = fields.Many2one(
        "assembly.assembly",
        string="Assembly",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Title", required=True)
    description = fields.Html()
    requires_vote = fields.Boolean(default=True)
    vote_item_type = fields.Selection(
        [
            ("yes_no", "Yes / No / Abstention / Blank"),
            ("multiple_options", "Multiple options"),
        ],
        string="Vote kind",
        default="yes_no",
        help=(
            "Yes/No for standard vote; "
            "Multiple options to show a list of choices on the ballot."
        ),
    )
    vote_type_id = fields.Many2one(
        "vote.type",
        string="Vote type",
        ondelete="restrict",
        domain="[('active', '=', True)]",
    )
    voting_ids = fields.One2many(
        "assembly.voting",
        "agenda_id",
        string="Votings",
    )
    option_ids = fields.One2many(
        "assembly.agenda.option",
        "agenda_id",
        string="Options",
        copy=True,
    )
    agenda_state = fields.Selection(
        [
            ("pending", "Pending"),
            ("in_progress", "In progress"),
            ("voted", "Voted"),
            ("skipped", "Skipped"),
        ],
        string="State",
        default="pending",
        required=True,
    )
    count_votings = fields.Integer(
        string="Votings count",
        compute="_compute_count_votings",
    )

    @api.depends("voting_ids")
    def _compute_count_votings(self):
        for rec in self:
            rec.count_votings = len(rec.voting_ids)

    @api.constrains("vote_type_id", "voting_ids")
    def _check_vote_type_no_votings(self):
        for rec in self:
            if rec.requires_vote and not rec.vote_type_id and rec.voting_ids:
                raise ValidationError(
                    self.env._("Vote type is required when the item requires a vote.")
                )

    @api.constrains("vote_type_id", "assembly_id")
    def _check_vote_type_in_assembly(self):
        for rec in self:
            if rec.vote_type_id and rec.assembly_id and rec.assembly_id.vote_type_ids:
                if rec.vote_type_id not in rec.assembly_id.vote_type_ids:
                    raise ValidationError(
                        self.env._(
                            "Vote type must be one of the assembly's vote types."
                        )
                    )

    def write(self, vals):
        if "vote_type_id" in vals:
            for rec in self:
                if rec.voting_ids:
                    raise ValidationError(
                        self.env._(
                            "Cannot change vote type when the agenda item "
                            "already has votings."
                        )
                    )
        return super().write(vals)

    def action_start_voting(self):
        self.ensure_one()
        if self.agenda_state not in ("pending", "in_progress"):
            raise ValidationError(self.env._("This item is not open for voting."))
        if self.requires_vote and not self.vote_type_id:
            raise ValidationError(self.env._("Set a vote type for this agenda item."))
        self.env["assembly.voting"].create(
            {
                "agenda_id": self.id,
                "vote_type_id": self.vote_type_id.id,
                "name": self.name,
                "voting_state": "open",
                "date_open": fields.Datetime.now(),
            }
        )
        self.agenda_state = "in_progress"

    def action_skip(self):
        self.ensure_one()
        self.agenda_state = "skipped"

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

    def action_open_votings(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Votings"),
            "res_model": "assembly.voting",
            "view_mode": "list,form",
            "domain": [("agenda_id", "=", self.id)],
            "context": {"default_agenda_id": self.id},
        }
