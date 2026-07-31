# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from .assembly_assembly import CTX_ASSEMBLY_INTERNAL_TRANSITION


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
        check_company=True,
    )
    agenda_vote_mode = fields.Selection(
        related="agenda_id.agenda_vote_mode",
        string="Vote mode",
        readonly=True,
    )
    assembly_id = fields.Many2one(
        "assembly.assembly",
        related="agenda_id.assembly_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="assembly_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    allow_online_voting = fields.Boolean(
        related="assembly_id.allow_online_voting",
        string="Allow online voting",
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
    count_recorded_votes = fields.Integer(
        string="Recorded votes",
        compute="_compute_voting_session_indicators",
    )
    count_pending_votes = fields.Integer(
        string="Pending votes",
        compute="_compute_voting_session_indicators",
    )
    remaining_votes = fields.Float(
        string="Remaining votes",
        compute="_compute_voting_session_indicators",
    )

    @api.depends(
        "vote_line_ids",
        "vote_line_ids.vote_option",
        "total_votes_possible",
        "total_votes_cast",
    )
    def _compute_voting_session_indicators(self):
        for record in self:
            lines = record.vote_line_ids
            voted = lines.filtered(lambda line: line.vote_option != "unset")
            record.count_recorded_votes = len(voted)
            record.count_pending_votes = len(lines) - len(voted)
            record.remaining_votes = (record.total_votes_possible or 0.0) - (
                record.total_votes_cast or 0.0
            )

    @api.depends("vote_line_ids", "result_ids")
    def _compute_count_lines_results(self):
        for record in self:
            record.count_vote_lines = len(record.vote_line_ids)
            record.count_results = len(record.result_ids)

    def action_open_agenda_item(self):
        return self._action_window(
            "assembly.agenda",
            self.env._("Agenda item"),
            "form",
            extra={"res_id": self.agenda_id.id},
        )

    def action_open_vote_lines(self):
        return self._action_window(
            "assembly.voting.line",
            self.env._("Votes cast"),
            "list,form",
            extra={
                "domain": [("voting_id", "=", self.id)],
                "context": {"default_voting_id": self.id},
            },
        )

    def action_open_session_control(self):
        self.ensure_one()
        view = self.env.ref(
            "base_assembly.assembly_voting_view_form_session",
            raise_if_not_found=False,
        )
        action = {
            "type": "ir.actions.act_window",
            "name": self.env._("Voting session"),
            "res_model": "assembly.voting",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
            "context": dict(self.env.context, form_view_initial_mode="edit"),
        }
        if view:
            action["views"] = [(view.id, "form")]
        return action

    def action_session_go_previous_agenda(self):
        self.ensure_one()
        return self.agenda_id.action_session_navigate_live_voting(-1)

    def action_session_go_next_agenda(self):
        self.ensure_one()
        return self.agenda_id.action_session_navigate_live_voting(1)

    def action_session_close_and_next(self):
        self.ensure_one()
        agenda = self.agenda_id
        self.action_close()
        return agenda.action_session_navigate_live_voting(1)

    def action_session_cancel_and_next(self):
        self.ensure_one()
        agenda = self.agenda_id
        self.action_cancel()
        return agenda.action_session_navigate_live_voting(1)

    def action_session_skip_agenda_item(self):
        self.ensure_one()
        agenda = self.agenda_id
        agenda.action_session_safe_skip()
        return agenda.action_session_navigate_live_voting(1)

    def _iter_roll_call_attendee_records(self):
        """Confirmed attendees with positive vote weight for this voting's type."""
        self.ensure_one()
        if not self.assembly_id or not self.vote_type_id:
            return self.env["assembly.attendee"].browse()
        attendee_vote_model = self.env["assembly.attendee.vote"]
        av_lines = attendee_vote_model.search(
            [
                ("vote_type_id", "=", self.vote_type_id.id),
                ("attendee_vote_total", ">", 0.0),
                ("attendee_id.assembly_id", "=", self.assembly_id.id),
                ("attendee_id.attendee_state", "=", "confirmed"),
            ]
        )
        return av_lines.mapped("attendee_id").sorted(
            lambda a: (a.partner_id.id or 0, a.id)
        )

    def _ensure_roll_call_lines(self):
        """Create missing ``unset`` lines for eligible attendees (idempotent)."""
        self.ensure_one()
        if self.voting_state != "open":
            return 0
        vote_line_model = self.env["assembly.voting.line"]
        created = 0
        for att in self._iter_roll_call_attendee_records():
            if vote_line_model.search(
                [("voting_id", "=", self.id), ("attendee_id", "=", att.id)], limit=1
            ):
                continue
            vote_line_model.create(
                {
                    "voting_id": self.id,
                    "attendee_id": att.id,
                    "vote_option": "unset",
                }
            )
            created += 1
        return created

    def action_refresh_roll_call(self):
        """Load or update the roll-call grid (add new rows; keep recorded votes)."""
        self.ensure_one()
        if self.voting_state != "open":
            raise UserError(
                self.env._("You can only refresh the roll call while voting is open.")
            )
        self._ensure_roll_call_lines()
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_open_results(self):
        return self._action_window(
            "assembly.voting.result",
            self.env._("Results"),
            "list,form",
            extra={
                "domain": [("voting_id", "=", self.id)],
                "context": {"default_voting_id": self.id},
            },
        )

    @api.constrains("name")
    def _check_name_non_empty(self):
        for record in self:
            if not (record.name or "").strip():
                raise ValidationError(self.env._("Voting description cannot be empty."))

    @api.constrains("agenda_id")
    def _check_agenda_is_weighted_mode(self):
        for record in self:
            if record.agenda_id and record.agenda_id.agenda_vote_mode != "weighted":
                raise ValidationError(
                    self.env._(
                        "Roll-call votings can only be linked to agenda items in "
                        "weighted (roll-call) mode."
                    )
                )

    @api.constrains("vote_type_id", "agenda_id")
    def _check_vote_type_consistent_with_agenda(self):
        for record in self:
            if not record.agenda_id or not record.vote_type_id:
                continue
            assembly = record.agenda_id.assembly_id
            if not assembly:
                continue
            avt = assembly.vote_type_ids
            if record.vote_type_id not in avt:
                raise ValidationError(
                    self.env._(
                        "The voting vote type must be one of the assembly's vote types."
                    )
                )
            if (
                record.agenda_id.requires_vote
                and record.agenda_id.vote_type_id
                and record.vote_type_id != record.agenda_id.vote_type_id
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
        agenda_ids = {v.get("agenda_id") for v in vals_list if v.get("agenda_id")}
        if agenda_ids:
            agendas = self.env["assembly.agenda"].browse(list(agenda_ids)).exists()
            agendas.mapped(
                "assembly_id"
            )._assembly_ensure_not_closed_for_related_changes()
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.context.get(CTX_ASSEMBLY_INTERNAL_TRANSITION):
            self.mapped("assembly_id")._assembly_ensure_not_closed_for_related_changes()
        return super().write(vals)

    def unlink(self):
        self.mapped("assembly_id")._assembly_ensure_not_closed_for_related_changes()
        return super().unlink()

    @api.depends(
        "vote_line_ids", "vote_line_ids.votes_applied", "agenda_id", "vote_type_id"
    )
    def _compute_totals(self):
        attendee_model = self.env["assembly.attendee"]
        attendee_vote_model = self.env["assembly.attendee.vote"]
        for record in self:
            lines_counted = record.vote_line_ids.filtered(
                lambda line: line.vote_option != "unset"
            )
            total_cast = sum(lines_counted.mapped("votes_applied"))
            possible = 0.0
            if record.agenda_id and record.vote_type_id:
                attendees = attendee_model._search_attendees_for_assembly(
                    record.assembly_id.id,
                    attendee_state="confirmed",
                )
                if attendees:
                    lines = attendee_vote_model.search(
                        [
                            ("attendee_id", "in", attendees.ids),
                            ("vote_type_id", "=", record.vote_type_id.id),
                        ]
                    )
                    possible = sum(lines.mapped("attendee_vote_total"))
            record.total_votes_cast = total_cast
            record.total_votes_possible = possible
            record.participation_percentage = (
                (total_cast / possible * 100.0) if possible else 0.0
            )

    def _cancel_other_open_votings_same_agenda(self):
        """Cancel extra open voting rows for the same agenda item (dedup)."""
        self.ensure_one()
        if not self.agenda_id:
            return
        others = self.env["assembly.voting"].search(
            [
                ("agenda_id", "=", self.agenda_id.id),
                ("id", "!=", self.id),
                ("voting_state", "=", "open"),
            ]
        )
        if others:
            others.write({"voting_state": "cancelled"})

    def action_close(self):
        for record in self:
            if record.voting_state != "open":
                raise UserError(self.env._("Only open votings can be closed."))
            record.write(
                {
                    "voting_state": "closed",
                    "date_close": fields.Datetime.now(),
                }
            )
            record._persist_closed_voting_results()  # pylint: disable=protected-access
            record.agenda_id.write({"agenda_state": "voted"})
            record._cancel_other_open_votings_same_agenda()

    def action_cancel(self):
        for record in self:
            if record.voting_state != "open":
                raise UserError(self.env._("Only open votings can be cancelled."))
            record.write({"voting_state": "cancelled"})

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
