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
    assembly_state = fields.Selection(
        string="Assembly state",
        related="assembly_id.assembly_state",
        readonly=True,
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
            (_AGENDA_VOTE_MODE_NO_VOTE, "No vote"),
            (_AGENDA_VOTE_MODE_WEIGHTED, "Weighted vote"),
            (_AGENDA_VOTE_MODE_MANUAL_YES_NO, "Manual vote (simple count)"),
            (_AGENDA_VOTE_MODE_MANUAL_MULTI, "Manual vote (multi-option)"),
        ],
        string="Vote mode",
        default=_AGENDA_VOTE_MODE_WEIGHTED,
        required=True,
        index=True,
        help=(
            "Weighted vote: each eligible attendee casts their own votes using the "
            "selected vote type; the system stores individual voting lines (roll-call). "
            "Manual modes: enter only aggregate totals (yes/no/abstain/blank or per "
            "ballot option counts); no per-attendee vote lines are created for this item. "
            "No vote: discussion or information only."
        ),
    )
    requires_vote = fields.Boolean(
        default=True,
        help=(
            "Only used in weighted vote mode. When enabled, opening a voting session "
            "records votes per attendee using the vote type. In manual and no-vote "
            "modes this stays off by design."
        ),
    )
    vote_type_id = fields.Many2one(
        "vote.type",
        string="Vote type",
        ondelete="restrict",
        domain=(
            "[('active', '=', True), ('id', 'in', assembly_allowed_vote_type_ids)]"
        ),
        help=(
            "Required in weighted vote mode. " "Must be one of the assembly vote types."
        ),
    )
    option_ids = fields.One2many(
        "assembly.agenda.option",
        "agenda_id",
        string="Voting options",
        help=(
            "Manual vote (multi-option): add one row per choice on the ballot. "
            "Use the Choice column for the label members see, and the Votes column for "
            "the final total count per choice. Only aggregate totals are stored; "
            "per-attendee votes are not recorded."
        ),
    )
    manual_yes = fields.Integer(
        string="Yes (total votes)",
        default=0,
        help=(
            "Final number of yes votes for this item. "
            "Only aggregate totals are stored; votes are not recorded per attendee."
        ),
    )
    manual_no = fields.Integer(
        string="No (total votes)",
        default=0,
        help=(
            "Final number of no votes for this item. "
            "Only aggregate totals are stored; votes are not recorded per attendee."
        ),
    )
    manual_abstain = fields.Integer(
        string="Abstention (total votes)",
        default=0,
        help=(
            "Final number of abstention votes for this item. "
            "Only aggregate totals are stored; votes are not recorded per attendee."
        ),
    )
    manual_count_blank = fields.Integer(
        string="Blank (total votes)",
        default=0,
        help=(
            "Final number of blank votes for this item. "
            "Only aggregate totals are stored; votes are not recorded per attendee."
        ),
    )
    manual_total_expected = fields.Float(
        string="Expected total votes",
        help=(
            "Reference total for validation. In manual vote (simple count), when non-zero, "
            "the sum of yes, no, abstention, and blank must match this value; when zero, "
            "rules still use attendee vote units when they can be computed. "
            "In manual vote (multi-option), the sum of option counts is checked the same way. "
            "This mode records final counts only, not how each member voted."
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
    manual_multi_options_count = fields.Integer(
        string="Option count",
        compute="_compute_manual_multi_ux_metrics",
    )
    manual_multi_votes_sum = fields.Integer(
        string="Sum of option votes",
        compute="_compute_manual_multi_ux_metrics",
    )
    session_manual_entered_total = fields.Float(
        string="Entered total votes",
        compute="_compute_session_manual_totals",
        help=(
            "Sum of yes, no, abstention, and blank (simple count) or sum of option votes "
            "(multi-option)."
        ),
    )
    session_manual_expected_display = fields.Float(
        string="Expected total votes (reference)",
        compute="_compute_session_manual_totals",
        help=(
            "Expected total from the field above when set; otherwise the total vote units "
            "from confirmed attendees when the system can compute them."
        ),
    )
    session_manual_delta = fields.Float(
        string="Difference vs expected total",
        compute="_compute_session_manual_totals",
        help="Entered total votes minus the reference expected total.",
    )
    session_manual_has_variance = fields.Boolean(
        string="Manual totals differ from expected",
        compute="_compute_session_manual_totals",
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

    @api.depends(
        "agenda_vote_mode",
        "option_ids",
        "option_ids.manual_vote_count",
    )
    def _compute_manual_multi_ux_metrics(self):
        for rec in self:
            rec.manual_multi_options_count = len(rec.option_ids)
            if rec.agenda_vote_mode == _AGENDA_VOTE_MODE_MANUAL_MULTI:
                rec.manual_multi_votes_sum = sum(
                    rec.option_ids.mapped("manual_vote_count")
                )
            else:
                rec.manual_multi_votes_sum = 0

    @api.depends(
        "agenda_vote_mode",
        "manual_yes",
        "manual_no",
        "manual_abstain",
        "manual_count_blank",
        "manual_total_expected",
        "option_ids.manual_vote_count",
        "assembly_id",
    )
    def _compute_session_manual_totals(self):
        for rec in self:
            if rec.agenda_vote_mode == _AGENDA_VOTE_MODE_MANUAL_YES_NO:
                entered = float(sum(getattr(rec, f) for f in _MANUAL_COUNT_FIELDS))
            elif rec.agenda_vote_mode == _AGENDA_VOTE_MODE_MANUAL_MULTI:
                entered = float(sum(rec.option_ids.mapped("manual_vote_count")))
            else:
                rec.session_manual_entered_total = 0.0
                rec.session_manual_expected_display = 0.0
                rec.session_manual_delta = 0.0
                rec.session_manual_has_variance = False
                continue
            possible = (
                float(rec.assembly_id._get_manual_yes_no_possible_vote_units())
                if rec.assembly_id
                else 0.0
            )
            expected = float(rec.manual_total_expected or 0.0)
            if float_is_zero(expected, precision_digits=6):
                exp_display = possible
            else:
                exp_display = expected
            rec.session_manual_entered_total = entered
            rec.session_manual_expected_display = exp_display
            rec.session_manual_delta = entered - exp_display
            rec.session_manual_has_variance = not float_is_zero(
                rec.session_manual_delta,
                precision_digits=6,
            )

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
                        "Expected total votes applies only in manual vote "
                        "(simple count) or manual vote (multi-option) mode."
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
                        "Weighted vote mode requires “Requires vote” to be enabled."
                    )
                )
            if rec.agenda_vote_mode != _AGENDA_VOTE_MODE_WEIGHTED and rec.requires_vote:
                raise ValidationError(
                    self.env._("“Requires vote” is only used in weighted vote mode.")
                )

    @api.constrains("agenda_vote_mode", "vote_type_id")
    def _check_vote_type_only_in_weighted_mode(self):
        for rec in self:
            if rec.agenda_vote_mode != _AGENDA_VOTE_MODE_WEIGHTED and rec.vote_type_id:
                raise ValidationError(
                    self.env._("Vote type is only allowed in weighted vote mode.")
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
                    self.env._("A vote type is required in weighted vote mode.")
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
                        "Yes/no/abstain/blank counts are not used in "
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
                            "Yes/no/abstain/blank counters apply "
                            "only in manual vote (simple count) mode."
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
                            "Manual vote counts must be zero when there are no votes "
                            "from confirmed attendees for this assembly."
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
                        "account for %(possible)s votes for this assembly's vote types.",
                        actual=actual,
                        possible=possible,
                    )
                )
            return

        if float_compare(self.manual_total_expected, possible, precision_digits=6) != 0:
            raise ValidationError(
                self.env._(
                    "Expected total votes (%(expected)s) does not match the "
                    "%(possible)s votes from confirmed attendees for the assembly "
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
                            "Cannot change vote mode while weighted vote sessions exist "
                            "for this agenda item."
                        )
                    )
        if "requires_vote" in vals and vals["requires_vote"]:
            for line in self:
                effective_mode = vals.get("agenda_vote_mode", line.agenda_vote_mode)
                if effective_mode != _AGENDA_VOTE_MODE_WEIGHTED:
                    raise ValidationError(
                        self.env._(
                            "“Requires vote” applies only in weighted vote mode."
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
                        "Manual finalization applies only to manual vote "
                        "(simple count) or manual vote (multi-option) modes."
                    )
                )
            if rec.agenda_state not in ("pending", "in_progress"):
                raise UserError(
                    self.env._("Only pending or in-progress items can be finalized.")
                )
            if rec.voting_ids.filtered(lambda v: v.voting_state == "open"):
                raise UserError(
                    self.env._(
                        "Close or cancel open weighted vote sessions before finalizing "
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
                    "A voting session can only be started in weighted vote mode."
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
        voting = self.env["assembly.voting"].create(
            {
                "agenda_id": self.id,
                "vote_type_id": self.vote_type_id.id,
                "name": self.name,
                "voting_state": "open",
                "date_open": fields.Datetime.now(),
            }
        )
        self.write({"agenda_state": "in_progress"})
        form_view = self.env.ref(
            "base_assembly.assembly_voting_view_form", raise_if_not_found=False
        )
        action = {
            "type": "ir.actions.act_window",
            "name": voting.name,
            "res_model": "assembly.voting",
            "res_id": voting.id,
            "view_mode": "form",
            "target": "current",
            "context": dict(self.env.context),
        }
        if form_view:
            action["views"] = [(form_view.id, "form")]
        return action

    def action_skip(self):
        self.ensure_one()
        self.write({"agenda_state": "skipped"})

    def action_session_safe_skip(self):
        for rec in self:
            open_v = rec.voting_ids.filtered(lambda v: v.voting_state == "open")
            if open_v:
                open_v.action_cancel()
            rec.action_skip()

    def action_session_manual_skip_and_next(self):
        self.ensure_one()
        self.action_session_safe_skip()
        return self.action_session_navigate_live_voting(1)

    def action_open_live_voting_screen(self):
        self.ensure_one()
        if self.agenda_vote_mode == _AGENDA_VOTE_MODE_NO_VOTE:
            raise UserError(self.env._("This agenda item does not include a vote."))
        if self.agenda_state == "skipped":
            raise UserError(self.env._("This agenda item was skipped."))
        if self.agenda_vote_mode == _AGENDA_VOTE_MODE_WEIGHTED:
            open_v = self.voting_ids.filtered(lambda v: v.voting_state == "open")[:1]
            if open_v:
                open_v._ensure_roll_call_lines()
                return open_v.action_open_session_control()
            _epoch = fields.Datetime.from_string("1970-01-01 00:00:00")
            closed_v = self.voting_ids.filtered(
                lambda v: v.voting_state == "closed"
            ).sorted(key=lambda v: v.date_close or _epoch, reverse=True)[:1]
            if closed_v and self.agenda_state == "voted":
                return closed_v.action_open_session_control()
            if self.agenda_state not in ("pending", "in_progress"):
                raise UserError(
                    self.env._("This agenda item is not open for live voting.")
                )
            self.action_start_voting()
            open_v = self.voting_ids.filtered(lambda v: v.voting_state == "open")[:1]
            if not open_v:
                raise UserError(
                    self.env._("Could not start a voting session for this item.")
                )
            open_v._ensure_roll_call_lines()
            return open_v.action_open_session_control()
        if self.agenda_vote_mode in (
            _AGENDA_VOTE_MODE_MANUAL_YES_NO,
            _AGENDA_VOTE_MODE_MANUAL_MULTI,
        ):
            if self.agenda_state not in ("pending", "in_progress", "voted"):
                raise UserError(
                    self.env._("This agenda item is not available for manual entry.")
                )
            view = self.env.ref(
                "base_assembly.assembly_agenda_view_form_session_manual",
                raise_if_not_found=False,
            )
            action = {
                "type": "ir.actions.act_window",
                "name": self.env._("Manual vote (session)"),
                "res_model": "assembly.agenda",
                "res_id": self.id,
                "view_mode": "form",
                "target": "current",
                "context": dict(self.env.context, form_view_initial_mode="edit"),
            }
            if view:
                action["views"] = [(view.id, "form")]
            return action
        raise UserError(self.env._("Unsupported vote mode for the live screen."))

    def action_session_manual_prev(self):
        self.ensure_one()
        return self.action_session_navigate_live_voting(-1)

    def action_session_manual_next(self):
        self.ensure_one()
        return self.action_session_navigate_live_voting(1)

    def action_session_navigate_live_voting(self, step):
        self.ensure_one()
        if not step:
            return self.action_open_live_voting_screen()
        items = self.assembly_id.agenda_ids.sorted(lambda a: (a.sequence, a.id))
        ids = items.ids
        if self.id not in ids:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": self.env._("Agenda"),
                    "message": self.env._(
                        "Could not find this item on the assembly agenda."
                    ),
                    "type": "warning",
                    "sticky": False,
                },
            }
        idx = ids.index(self.id)
        new_idx = idx + int(step)
        if new_idx < 0 or new_idx >= len(ids):
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": self.env._("Agenda"),
                    "message": self.env._("No adjacent agenda item in that direction."),
                    "type": "info",
                    "sticky": False,
                },
            }
        target = items[new_idx]
        try:
            return target.action_open_live_voting_screen()
        except UserError as err:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": self.env._("Agenda"),
                    "message": str(err),
                    "type": "warning",
                    "sticky": False,
                },
            }

    def action_open_votings(self):
        return self._action_window(
            "assembly.voting",
            self.env._("Votings"),
            "list,kanban,graph,pivot,form",
            domain=[("agenda_id", "=", self.id)],
            context={"default_agenda_id": self.id},
        )
