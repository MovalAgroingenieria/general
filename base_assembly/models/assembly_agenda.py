# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AssemblyAgenda(models.Model):
    _name = "assembly.agenda"
    _inherit = ["assembly.mixin.open.assembly"]
    _description = "Assembly agenda item"
    _order = "assembly_id, sequence, id"

    assembly_id = fields.Many2one(
        "assembly.assembly",
        string="Assembly",
        required=True,
        ondelete="cascade",
        index=True,
    )
    assembly_allowed_vote_type_ids = fields.Many2many(
        "vote.type",
        related="assembly_id.vote_type_ids",
        string="Assembly vote types",
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Title", required=True)
    description = fields.Html()
    requires_vote = fields.Boolean(default=True)
    vote_type_id = fields.Many2one(
        "vote.type",
        string="Vote type",
        ondelete="restrict",
        domain=(
            "[('active', '=', True), ('id', 'in', assembly_allowed_vote_type_ids)]"
        ),
        help=(
            "Required when 'Requires vote' is enabled. "
            "Must be selected from the assembly's vote types. "
            "Cannot be changed once voting has started."
        ),
    )
    voting_ids = fields.One2many(
        "assembly.voting",
        "agenda_id",
        string="Votings",
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

    _sql_constraints = [
        (
            "assembly_agenda_assembly_sequence_uniq",
            "UNIQUE(assembly_id, sequence)",
            "Sequence must be unique per assembly.",
        ),
    ]

    @api.depends("voting_ids")
    def _compute_count_votings(self):
        for line in self:
            line.count_votings = len(line.voting_ids)

    @api.constrains("requires_vote", "vote_type_id")
    def _check_vote_type_required_when_requires_vote(self):
        for line in self:
            if line.requires_vote and not line.vote_type_id:
                raise ValidationError(
                    self.env._(
                        "A vote type must be specified when the agenda item "
                        "requires a vote. Please select a vote type or "
                        "uncheck 'Requires vote'."
                    )
                )

    @api.constrains("vote_type_id", "assembly_id")
    def _check_vote_type_in_assembly(self):
        for line in self:
            if not line.vote_type_id or not line.assembly_id:
                continue
            assembly_vote_types = line.assembly_id.vote_type_ids
            if not assembly_vote_types:
                raise ValidationError(
                    self.env._(
                        "Vote type '%(vote_type)s' cannot be used because the assembly "
                        "has no vote types configured.",
                        vote_type=line.vote_type_id.name,
                    )
                )
            if line.vote_type_id not in assembly_vote_types:
                raise ValidationError(
                    self.env._(
                        "Vote type '%(vote_type)s' must be one of "
                        "the assembly's vote types. "
                        "Available types: %(available)s",
                        vote_type=line.vote_type_id.name,
                        available=", ".join(assembly_vote_types.mapped("name")),
                    )
                )

    def _assert_agenda_vote_type_constraints_after_write(self):
        self._check_vote_type_required_when_requires_vote()
        self._check_vote_type_in_assembly()

    def _validate_agenda_write_vals(self, vals):
        if "vote_type_id" in vals:
            for line in self:
                if not line.voting_ids:
                    continue
                new_id = vals["vote_type_id"]
                current_id = line.vote_type_id.id if line.vote_type_id else False
                if new_id != current_id:
                    raise ValidationError(
                        self.env._(
                            "The vote type cannot be changed because the agenda item "
                            "already has votings. Once voting has started, "
                            "the vote type becomes immutable."
                        )
                    )
        if "requires_vote" in vals and vals["requires_vote"]:
            for line in self:
                vote_type_id = vals.get(
                    "vote_type_id",
                    line.vote_type_id.id if line.vote_type_id else False,
                )
                if not vote_type_id:
                    raise ValidationError(
                        self.env._(
                            "A vote type must be specified when the agenda item "
                            "requires a vote. Please select a vote type before "
                            "enabling 'Requires vote'."
                        )
                    )
        if "vote_type_id" in vals and not vals["vote_type_id"]:
            for line in self:
                will_require_vote = vals.get("requires_vote", line.requires_vote)
                if will_require_vote:
                    raise ValidationError(
                        self.env._(
                            "The vote type cannot be cleared while 'Requires vote' "
                            "is enabled. Please either select a vote type or "
                            "disable 'Requires vote' first."
                        )
                    )

    @api.model_create_multi
    def create(self, vals_list):
        asm_ids = {v.get("assembly_id") for v in vals_list if v.get("assembly_id")}
        if asm_ids:
            self.env["assembly.assembly"].browse(
                list(asm_ids)
            ).exists()._assembly_ensure_not_closed_for_related_changes()
        agendas = super().create(vals_list)
        agendas._assert_agenda_vote_type_constraints_after_write()
        return agendas

    def write(self, vals):
        self.mapped("assembly_id")._assembly_ensure_not_closed_for_related_changes()
        self._validate_agenda_write_vals(vals)
        res = super().write(vals)
        self._assert_agenda_vote_type_constraints_after_write()
        return res

    def unlink(self):
        self.mapped("assembly_id")._assembly_ensure_not_closed_for_related_changes()
        return super().unlink()

    def action_start_voting(self):
        self.ensure_one()
        if self.agenda_state not in ("pending", "in_progress"):
            raise ValidationError(self.env._("This item is not open for voting."))
        if self.requires_vote and not self.vote_type_id:
            raise ValidationError(self.env._("Set a vote type for this agenda item."))
        open_votings = self.voting_ids.filtered(lambda v: v.voting_state == "open")
        if open_votings:
            raise ValidationError(
                self.env._(
                    "This agenda item already has an open voting. "
                    "Close or cancel it before starting a new one."
                )
            )
        self.env["assembly.voting"].create(
            {
                "agenda_id": self.id,
                "vote_type_id": self.vote_type_id.id,
                "name": self.name,
                "voting_state": "open",
                "date_open": fields.Datetime.now(),
            }
        )
        self.write({"agenda_state": "in_progress"})

    def action_skip(self):
        self.ensure_one()
        self.write({"agenda_state": "skipped"})

    def action_open_votings(self):
        return self._action_window(
            "assembly.voting",
            self.env._("Votings"),
            "list,kanban,graph,pivot,form",
            domain=[("agenda_id", "=", self.id)],
            context={"default_agenda_id": self.id},
        )
