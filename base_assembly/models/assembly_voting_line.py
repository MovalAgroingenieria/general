# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare

_VOTES_APPLIED_FLOAT_DIGITS = 6


class AssemblyVotingLine(models.Model):
    _name = "assembly.voting.line"
    _description = "Voting line (cast vote)"
    _order = "partner_id, attendee_id, id"

    voting_id = fields.Many2one(
        "assembly.voting",
        string="Voting",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    assembly_id = fields.Many2one(
        "assembly.assembly",
        string="Assembly",
        related="voting_id.assembly_id",
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
    attendee_id = fields.Many2one(
        "assembly.attendee",
        string="Attendee",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        related="attendee_id.partner_id",
        store=True,
        readonly=True,
    )
    vote_option = fields.Selection(
        [
            ("unset", "Not recorded"),
            ("yes", "Yes"),
            ("no", "No"),
            ("abstention", "Abstention"),
            ("blank", "Blank"),
        ],
        string="Vote",
        default="unset",
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
    session_context_label = fields.Char(
        string="Delegation / representation",
        compute="_compute_session_context_label",
    )
    session_row_group_order = fields.Integer(
        compute="_compute_session_row_group_order",
        store=True,
    )
    session_row_status_label = fields.Char(
        string="Recording status",
        compute="_compute_session_row_ui",
    )
    session_control_state = fields.Selection(
        [
            ("pending", "Pending"),
            ("recorded", "Recorded"),
            ("ineligible", "Not eligible"),
        ],
        string="Status",
        compute="_compute_session_row_ui",
    )

    @api.depends(
        "attendee_id",
        "attendee_id.call_register_has_representation",
        "attendee_id.call_register_representation_agent",
        "attendee_id.call_register_has_inbound_delegation",
        "attendee_id.call_register_has_outbound_delegation",
        "attendee_id.participant_partner_id",
    )
    def _compute_session_context_label(self):
        for line in self:
            att = line.attendee_id
            if not att:
                line.session_context_label = ""
                continue
            parts = []
            if (
                att.participant_partner_id
                and att.participant_partner_id != att.partner_id
            ):
                parts.append(
                    self.env._(
                        "Representing %(name)s",
                        name=att.participant_partner_id.display_name,
                    )
                )
            if (
                att.call_register_has_representation
                and att.call_register_representation_agent
            ):
                parts.append(
                    self.env._(
                        "Representation: %(agent)s",
                        agent=att.call_register_representation_agent,
                    )
                )
            if att.call_register_has_inbound_delegation:
                parts.append(self.env._("Receives delegated votes"))
            if att.call_register_has_outbound_delegation:
                parts.append(self.env._("Votes delegated out"))
            line.session_context_label = " · ".join(parts) if parts else ""

    @api.depends("vote_option", "votes_applied")
    def _compute_session_row_group_order(self):
        for line in self:
            if (
                float_compare(
                    line.votes_applied,
                    0.0,
                    precision_digits=_VOTES_APPLIED_FLOAT_DIGITS,
                )
                <= 0
            ):
                line.session_row_group_order = 3
            elif line.vote_option == "unset":
                line.session_row_group_order = 1
            else:
                line.session_row_group_order = 2

    @api.depends("vote_option", "votes_applied")
    def _compute_session_row_ui(self):
        for line in self:
            if (
                float_compare(
                    line.votes_applied,
                    0.0,
                    precision_digits=_VOTES_APPLIED_FLOAT_DIGITS,
                )
                <= 0
            ):
                line.session_control_state = "ineligible"
                line.session_row_status_label = self.env._("Not eligible")
            elif line.vote_option == "unset":
                line.session_control_state = "pending"
                line.session_row_status_label = self.env._("Pending")
            else:
                line.session_control_state = "recorded"
                line.session_row_status_label = self.env._("Recorded")

    _sql_constraints = [
        (
            "voting_attendee_uniq",
            "UNIQUE(voting_id, attendee_id)",
            "Each attendee can vote only once per voting.",
        ),
    ]

    @api.model
    def _apply_audit_defaults_to_voting_line_create_vals(self, vals_list):
        now = fields.Datetime.now()
        for vals in vals_list:
            opt = vals.get("vote_option", "unset")
            if opt == "unset":
                vals.setdefault("vote_cast_at", False)
                vals.setdefault("vote_cast_by_user_id", False)
                continue
            if "vote_cast_at" not in vals:
                vals["vote_cast_at"] = now
            if (
                "vote_cast_by_user_id" not in vals
                and self.env.user
                and self.env.user.id
            ):
                vals["vote_cast_by_user_id"] = self.env.uid

    @api.model
    def _set_votes_applied_snapshot_on_create_vals(self, vals):
        """Freeze ``votes_applied`` from ``assembly.attendee.vote`` at create time only."""
        voting = self.env["assembly.voting"].browse(vals["voting_id"])
        attendee = self.env["assembly.attendee"].browse(vals["attendee_id"])
        vote_type = voting.vote_type_id
        av = attendee.attendee_vote_ids.filtered(
            lambda v, vt=vote_type: v.vote_type_id == vt
        )[:1]
        if not av or av.attendee_vote_total <= 0:
            raise ValidationError(
                self.env._(
                    "This attendee has no votes for this vote type (delegated out)."
                )
            )
        total = av.attendee_vote_total
        if "votes_applied" in vals:
            if (
                float_compare(
                    vals["votes_applied"],
                    total,
                    precision_digits=_VOTES_APPLIED_FLOAT_DIGITS,
                )
                != 0
            ):
                raise ValidationError(
                    self.env._(
                        "Votes applied must match the attendee's vote total for "
                        "this type."
                    )
                )
        vals["votes_applied"] = total

    def write(self, vals):
        self.mapped("assembly_id")._assembly_ensure_not_closed_for_related_changes()
        if "votes_applied" in vals:
            for line in self:
                if (
                    float_compare(
                        vals["votes_applied"],
                        line.votes_applied,
                        precision_digits=_VOTES_APPLIED_FLOAT_DIGITS,
                    )
                    != 0
                ):
                    raise ValidationError(
                        self.env._(
                            "Votes applied is frozen at cast time and cannot be "
                            "changed."
                        )
                    )
        res = super().write(vals)
        to_stamp = self.filtered(
            lambda line: line.vote_option
            and line.vote_option != "unset"
            and not line.vote_cast_at
        )
        if to_stamp:
            to_stamp.sudo().write(
                {
                    "vote_cast_at": fields.Datetime.now(),
                    "vote_cast_by_user_id": self.env.uid,
                }
            )
        return res

    def unlink(self):
        self.mapped("assembly_id")._assembly_ensure_not_closed_for_related_changes()
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        vids = {v.get("voting_id") for v in vals_list if v.get("voting_id")}
        if vids:
            self.env["assembly.voting"].browse(list(vids)).exists().mapped(
                "assembly_id"
            )._assembly_ensure_not_closed_for_related_changes()
        self._apply_audit_defaults_to_voting_line_create_vals(vals_list)
        for vals in vals_list:
            self._set_votes_applied_snapshot_on_create_vals(vals)
        return super().create(vals_list)

    def _session_require_open_voting(self):
        for line in self:
            if line.voting_id.voting_state != "open":
                raise UserError(
                    self.env._(
                        "Votes can only be changed while the voting session is open."
                    )
                )

    def _session_write_vote_option(self, option):
        self._session_require_open_voting()
        vals = {"vote_option": option}
        if option == "unset":
            vals["vote_cast_at"] = False
            vals["vote_cast_by_user_id"] = False
        return self.write(vals)

    def action_session_vote_yes(self):
        return self._session_write_vote_option("yes")

    def action_session_vote_no(self):
        return self._session_write_vote_option("no")

    def action_session_vote_abstention(self):
        return self._session_write_vote_option("abstention")

    def action_session_vote_blank(self):
        return self._session_write_vote_option("blank")

    def action_session_vote_clear(self):
        return self._session_write_vote_option("unset")

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

    @api.constrains("attendee_id", "voting_id")
    def _check_attendee_same_assembly_as_voting(self):
        for line in self:
            if not line.attendee_id or not line.voting_id:
                continue
            if line.attendee_id.assembly_id != line.voting_id.assembly_id:
                raise ValidationError(
                    self.env._(
                        "The attendee must belong to the same assembly as this voting."
                    )
                )

    @api.constrains("attendee_id")
    def _check_attendee_not_absent_for_vote_line(self):
        for line in self:
            if line.attendee_id and line.attendee_id.attendee_state == "absent":
                raise ValidationError(
                    self.env._(
                        "You cannot record a vote for an attendee marked absent."
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
