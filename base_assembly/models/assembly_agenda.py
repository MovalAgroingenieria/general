# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero

_AGENDA_VOTE_MODE_WEIGHTED = "weighted"
_AGENDA_VOTE_MODE_NO_VOTE = "no_vote"
_AGENDA_VOTE_MODE_MANUAL_YES_NO = "manual_yes_no"
_AGENDA_VOTE_MODE_MANUAL_MULTI = "manual_multi"

_MANUAL_COUNT_FIELDS = (
    "manual_yes",
    "manual_no",
    "manual_abstain",
    "manual_count_blank",
)


class AssemblyAgenda(models.Model):
    _name = "assembly.agenda"
    _inherit = ["mail.thread", "assembly.mixin.open.assembly"]
    _description = "Assembly agenda item"
    _order = "assembly_id, sequence, id"

    assembly_id = fields.Many2one(
        "assembly.assembly",
        string="Assembly",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="assembly_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    assembly_allowed_vote_type_ids = fields.Many2many(
        "vote.type",
        related="assembly_id.vote_type_ids",
        string="Assembly vote types",
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Title", required=True, translate=True)
    description = fields.Html()
    agenda_vote_mode = fields.Selection(
        [
            (_AGENDA_VOTE_MODE_NO_VOTE, "No Vote"),
            (_AGENDA_VOTE_MODE_WEIGHTED, "Weighted"),
            (_AGENDA_VOTE_MODE_MANUAL_YES_NO, "Manual Yes/No"),
            (_AGENDA_VOTE_MODE_MANUAL_MULTI, "Manual Multi Option"),
        ],
        string="Vote mode",
        default=_AGENDA_VOTE_MODE_WEIGHTED,
        required=True,
        index=True,
    )
    requires_vote = fields.Boolean(
        default=True,
        help="True when using weighted (roll-call) voting; False for other modes.",
    )
    vote_type_id = fields.Many2one(
        "vote.type",
        string="Vote type",
        ondelete="restrict",
        domain=(
            "[('active', '=', True), ('id', 'in', assembly_allowed_vote_type_ids)]"
        ),
        help=(
            "Required in weighted (roll-call) mode. "
            "Must be one of the assembly vote types."
        ),
    )
    option_ids = fields.One2many(
        "assembly.agenda.option",
        "agenda_id",
        string="Ballot options",
        help="Used only in manual multi-option mode.",
    )
    manual_yes = fields.Integer(string="Manual yes", default=0)
    manual_no = fields.Integer(string="Manual no", default=0)
    manual_abstain = fields.Integer(string="Manual abstain", default=0)
    manual_count_blank = fields.Integer(string="Manual blank", default=0)
    manual_total_expected = fields.Float(
        string="Expected total vote units",
        help=(
            "Manual yes/no: when greater than zero, the four counters must sum to this "
            "value and it must match the vote units held by confirmed attendees "
            "(when that total can be computed). When zero, the counters must still "
            "match that attendee total if it is computable (>0); otherwise only the "
            "four-way sum vs this field is checked when the field is set. "
            "Not applied to manual multi-option totals."
        ),
    )
    final_summary = fields.Html(
        string="Final summary",
        help=(
            "Optional HTML notes for this agenda item (e.g. after closing). "
            "Not filled automatically by the system."
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

    @api.onchange("agenda_vote_mode")
    def _onchange_agenda_vote_mode(self):
        if self.agenda_vote_mode == _AGENDA_VOTE_MODE_WEIGHTED:
            self.requires_vote = True
        else:
            self.requires_vote = False
            self.vote_type_id = False

    @api.model
    def _sync_requires_vote_from_mode_vals(self, vals):
        """Align ``requires_vote``, ``vote_type_id``, and manual-only fields when mode changes."""
        vals = dict(vals)
        if "agenda_vote_mode" not in vals:
            return vals
        mode = vals["agenda_vote_mode"]
        if mode == _AGENDA_VOTE_MODE_WEIGHTED:
            vals["requires_vote"] = True
        else:
            vals["requires_vote"] = False
            vals["vote_type_id"] = False
        if mode not in (
            _AGENDA_VOTE_MODE_MANUAL_YES_NO,
            _AGENDA_VOTE_MODE_MANUAL_MULTI,
        ):
            vals["manual_total_expected"] = 0.0
        if mode != _AGENDA_VOTE_MODE_MANUAL_YES_NO:
            for fname in _MANUAL_COUNT_FIELDS:
                vals[fname] = 0
        return vals

    @api.constrains("agenda_vote_mode", "manual_total_expected")
    def _check_manual_total_expected_only_in_manual_modes(self):
        """``manual_total_expected`` is meaningful only for manual yes/no and manual multi."""
        for rec in self:
            if rec.agenda_vote_mode in (
                _AGENDA_VOTE_MODE_MANUAL_YES_NO,
                _AGENDA_VOTE_MODE_MANUAL_MULTI,
            ):
                continue
            if not float_is_zero(rec.manual_total_expected or 0.0, precision_digits=6):
                raise ValidationError(
                    self.env._(
                        "Expected total vote units applies only in manual yes/no or "
                        "manual multi-option mode."
                    )
                )

    @api.constrains("agenda_vote_mode", "requires_vote")
    def _check_requires_vote_matches_mode(self):
        for rec in self:
            if (
                rec.agenda_vote_mode == _AGENDA_VOTE_MODE_WEIGHTED
                and not rec.requires_vote
            ):
                raise ValidationError(
                    self.env._(
                        "Weighted (roll-call) mode requires “Requires vote” to be enabled."
                    )
                )
            if rec.agenda_vote_mode != _AGENDA_VOTE_MODE_WEIGHTED and rec.requires_vote:
                raise ValidationError(
                    self.env._(
                        "“Requires vote” is only used in weighted (roll-call) mode."
                    )
                )

    @api.constrains("agenda_vote_mode", "vote_type_id")
    def _check_vote_type_only_in_weighted_mode(self):
        for rec in self:
            if rec.agenda_vote_mode != _AGENDA_VOTE_MODE_WEIGHTED and rec.vote_type_id:
                raise ValidationError(
                    self.env._(
                        "Vote type is only allowed in weighted (roll-call) mode."
                    )
                )

    @api.constrains("agenda_vote_mode", "requires_vote", "vote_type_id")
    def _check_vote_type_required_in_weighted_mode(self):
        for rec in self:
            if (
                rec.agenda_vote_mode == _AGENDA_VOTE_MODE_WEIGHTED
                and rec.requires_vote
                and not rec.vote_type_id
            ):
                raise ValidationError(
                    self.env._("A vote type is required in weighted (roll-call) mode.")
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

    @api.constrains("agenda_vote_mode", "option_ids")
    def _check_option_ids_coherence_with_vote_mode(self):
        """Options exist iff mode is ``manual_multi`` (one constraint, two rules)."""
        for rec in self:
            if (
                rec.agenda_vote_mode != _AGENDA_VOTE_MODE_MANUAL_MULTI
                and rec.option_ids
            ):
                raise ValidationError(
                    self.env._(
                        "Ballot options are only allowed in manual multi-option mode."
                    )
                )
            if (
                rec.agenda_vote_mode == _AGENDA_VOTE_MODE_MANUAL_MULTI
                and not rec.option_ids
            ):
                raise ValidationError(
                    self.env._(
                        "Manual multi-option mode requires at least one ballot option."
                    )
                )

    @api.constrains(
        "agenda_vote_mode",
        "manual_yes",
        "manual_no",
        "manual_abstain",
        "manual_count_blank",
    )
    def _check_manual_yes_no_counters_scope(self):
        for rec in self:
            total_manual = sum(getattr(rec, f) for f in _MANUAL_COUNT_FIELDS)
            if rec.agenda_vote_mode == _AGENDA_VOTE_MODE_MANUAL_MULTI and total_manual:
                raise ValidationError(
                    self.env._(
                        "Yes/no/abstention/blank manual counts are not used in "
                        "manual multi-option mode; use ballot options instead."
                    )
                )
            if rec.agenda_vote_mode in (
                _AGENDA_VOTE_MODE_NO_VOTE,
                _AGENDA_VOTE_MODE_WEIGHTED,
            ):
                if total_manual:
                    raise ValidationError(
                        self.env._(
                            "Manual yes/no, abstention, and blank counters apply "
                            "only in manual yes/no mode."
                        )
                    )
            for f in _MANUAL_COUNT_FIELDS:
                if getattr(rec, f) < 0:
                    raise ValidationError(
                        self.env._("Manual vote counts cannot be negative.")
                    )

    @api.constrains(
        "manual_total_expected",
        "manual_yes",
        "manual_no",
        "manual_abstain",
        "manual_count_blank",
        "agenda_vote_mode",
        "option_ids",
    )
    def _check_manual_expected_total_sum(self):
        for rec in self:
            if rec.agenda_vote_mode not in (
                _AGENDA_VOTE_MODE_MANUAL_YES_NO,
                _AGENDA_VOTE_MODE_MANUAL_MULTI,
            ):
                continue
            rec._validate_manual_expected_total_for_mode()

    def _validate_manual_expected_total_for_mode(self):
        self.ensure_one()
        if self.agenda_vote_mode == _AGENDA_VOTE_MODE_MANUAL_MULTI:
            actual = float(sum(self.option_ids.mapped("manual_vote_count")))
            possible = float(self.assembly_id._get_manual_yes_no_possible_vote_units())
            self._compare_manual_totals_to_possible(actual, possible)
            return
        if self.agenda_vote_mode != _AGENDA_VOTE_MODE_MANUAL_YES_NO:
            return

        actual = float(sum(getattr(self, f) for f in _MANUAL_COUNT_FIELDS))
        possible = float(self.assembly_id._get_manual_yes_no_possible_vote_units())
        self._compare_manual_totals_to_possible(actual, possible)

    def _compare_manual_totals_to_possible(self, actual, possible):
        """Shared rules for manual yes/no and manual multi-option (AF v2.0 §2.3)."""
        self.ensure_one()
        if float_is_zero(possible, precision_digits=6):
            if self.manual_total_expected is None or float_is_zero(
                self.manual_total_expected, precision_digits=6
            ):
                if not float_is_zero(actual, precision_digits=6):
                    raise ValidationError(
                        self.env._(
                            "Manual vote counts must be zero when there are no vote "
                            "units from confirmed attendees for this assembly."
                        )
                    )
                return
            if (
                float_compare(actual, self.manual_total_expected, precision_digits=6)
                != 0
            ):
                raise ValidationError(
                    self.env._(
                        "Manual counts sum to %(actual)s but expected total is %(expected)s.",
                        actual=actual,
                        expected=self.manual_total_expected,
                    )
                )
            return

        if self.manual_total_expected is None or float_is_zero(
            self.manual_total_expected, precision_digits=6
        ):
            if float_compare(actual, possible, precision_digits=6) != 0:
                raise ValidationError(
                    self.env._(
                        "Manual vote counts sum to %(actual)s but confirmed attendees "
                        "hold %(possible)s vote units for this assembly's vote types.",
                        actual=actual,
                        possible=possible,
                    )
                )
            return

        if float_compare(self.manual_total_expected, possible, precision_digits=6) != 0:
            raise ValidationError(
                self.env._(
                    "Expected total vote units (%(expected)s) does not match the "
                    "%(possible)s units held by confirmed attendees for the assembly "
                    "vote types.",
                    expected=self.manual_total_expected,
                    possible=possible,
                )
            )
        if float_compare(actual, self.manual_total_expected, precision_digits=6) != 0:
            raise ValidationError(
                self.env._(
                    "Manual counts sum to %(actual)s but expected total is %(expected)s.",
                    actual=actual,
                    expected=self.manual_total_expected,
                )
            )

    def _assert_agenda_vote_type_constraints_after_write(self):
        self._check_vote_type_required_in_weighted_mode()
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
        if "agenda_vote_mode" in vals:
            for line in self:
                if (
                    line.voting_ids
                    and vals["agenda_vote_mode"] != line.agenda_vote_mode
                ):
                    raise ValidationError(
                        self.env._(
                            "Cannot change vote mode while roll-call votings exist "
                            "for this agenda item."
                        )
                    )
        if "requires_vote" in vals and vals["requires_vote"]:
            for line in self:
                effective_mode = vals.get("agenda_vote_mode", line.agenda_vote_mode)
                if effective_mode != _AGENDA_VOTE_MODE_WEIGHTED:
                    raise ValidationError(
                        self.env._(
                            "“Requires vote” applies only in weighted (roll-call) mode."
                        )
                    )
                vote_type_id = vals.get(
                    "vote_type_id",
                    line.vote_type_id.id if line.vote_type_id else False,
                )
                if not vote_type_id:
                    raise ValidationError(
                        self.env._(
                            "A vote type must be specified when enabling requires vote "
                            "in weighted mode."
                        )
                    )
        if "vote_type_id" in vals and not vals["vote_type_id"]:
            for line in self:
                effective_mode = vals.get("agenda_vote_mode", line.agenda_vote_mode)
                if effective_mode == _AGENDA_VOTE_MODE_WEIGHTED and (
                    vals.get("requires_vote", line.requires_vote)
                ):
                    raise ValidationError(
                        self.env._(
                            "The vote type cannot be cleared in weighted mode while "
                            "requires vote is enabled."
                        )
                    )

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for vals in vals_list:
            v = dict(vals)
            if "agenda_vote_mode" not in v:
                v["agenda_vote_mode"] = (
                    _AGENDA_VOTE_MODE_WEIGHTED
                    if v.get("requires_vote", True)
                    else _AGENDA_VOTE_MODE_NO_VOTE
                )
            v = self._sync_requires_vote_from_mode_vals(v)
            prepared.append(v)
        vals_list = prepared
        asm_ids = {v.get("assembly_id") for v in vals_list if v.get("assembly_id")}
        if asm_ids:
            self.env["assembly.assembly"].browse(
                list(asm_ids)
            ).exists()._assembly_ensure_not_closed_for_related_changes()
        agendas = super().create(vals_list)
        agendas._assert_agenda_vote_type_constraints_after_write()
        return agendas

    def write(self, vals):
        vals = self._sync_requires_vote_from_mode_vals(vals)
        self.mapped("assembly_id")._assembly_ensure_not_closed_for_related_changes()
        self._validate_agenda_write_vals(vals)
        res = super().write(vals)
        self._assert_agenda_vote_type_constraints_after_write()
        return res

    def unlink(self):
        self.mapped("assembly_id")._assembly_ensure_not_closed_for_related_changes()
        return super().unlink()

    def _validate_manual_finalize(self):
        self.ensure_one()
        if self.agenda_vote_mode == _AGENDA_VOTE_MODE_MANUAL_MULTI:
            if not self.option_ids:
                raise ValidationError(
                    self.env._(
                        "Add at least one ballot option before closing this point."
                    )
                )
        self._validate_manual_expected_total_for_mode()
        for f in _MANUAL_COUNT_FIELDS:
            if getattr(self, f) < 0:
                raise ValidationError(
                    self.env._("Manual vote counts cannot be negative.")
                )

    def action_finalize_manual(self):
        """Close a manual-mode agenda item (sets state to voted)."""
        for rec in self:
            if rec.agenda_vote_mode not in (
                _AGENDA_VOTE_MODE_MANUAL_YES_NO,
                _AGENDA_VOTE_MODE_MANUAL_MULTI,
            ):
                raise UserError(
                    self.env._(
                        "Manual finalization applies only to manual yes/no or "
                        "manual multi-option modes."
                    )
                )
            if rec.agenda_state not in ("pending", "in_progress"):
                raise UserError(
                    self.env._("Only pending or in-progress items can be finalized.")
                )
            if rec.voting_ids.filtered(lambda v: v.voting_state == "open"):
                raise UserError(
                    self.env._(
                        "Close or cancel open roll-call votings before finalizing "
                        "a manual-mode item."
                    )
                )
            rec._validate_manual_finalize()
            rec.write({"agenda_state": "voted"})

    def action_start_voting(self):
        self.ensure_one()
        if self.agenda_vote_mode != _AGENDA_VOTE_MODE_WEIGHTED:
            raise ValidationError(
                self.env._(
                    "Roll-call voting can only be started in weighted (roll-call) mode."
                )
            )
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
