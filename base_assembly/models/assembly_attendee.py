# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
# pylint: disable=too-many-lines

import re
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from psycopg2 import IntegrityError, errorcodes

_ATTENDEE_STATE_KEYS = frozenset({"registered", "confirmed", "absent"})

# Stored ``assembly.attendee.vote`` rows are rebuilt only through
# :meth:`AssemblyAttendee.recompute_votes` (see that method for the full trigger list).
# :meth:`write` on attendees never recomputes votes.
_ATTENDEE_ALLOWED_STATE_TRANSITIONS = {
    "registered": frozenset({"confirmed", "absent"}),
    "confirmed": frozenset({"absent"}),
    "absent": frozenset({"confirmed"}),
}

# ``write()`` safety: registration state and identity are not generic form fields.
# See :meth:`AssemblyAttendee.write`.
CTX_ATTENDEE_ALLOW_IDENTITY_WRITE = "assembly_attendee_allow_identity_write"
CTX_ATTENDEE_ALLOW_REGISTRATION_STATE_WRITE = (
    "assembly_attendee_allow_registration_state_write"
)


class AssemblyAttendee(models.Model):
    """Assembly member row; quorum uses presence state only, votes use ``partner_id``."""

    _name = "assembly.attendee"
    _inherit = ["assembly.mixin.open.assembly"]
    _description = "Assembly attendee"
    _order = "assembly_id, partner_id"
    _rec_name = "name"
    _rec_names_search = [
        "name",
        "partner_id.name",
        "partner_id.vat",
        "participant_partner_id.name",
    ]

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
    partner_id = fields.Many2one(
        "res.partner",
        string="Member",
        required=True,
        ondelete="cascade",
        index=True,
        help=(
            "Member holding this assembly seat. Quorum, delegations, and vote rows "
            "are keyed to this partner (not to the attendance contact)."
        ),
    )
    participant_partner_id = fields.Many2one(
        "res.partner",
        string="Present as",
        ondelete="set null",
        index=True,
        help=(
            "Contact who is physically present or signs for the member (e.g. proxy). "
            "Defaults to the member. Informational for lists and signatures; voting "
            "rights remain with Member."
        ),
    )
    name = fields.Char(
        string="Display name",
        compute="_compute_name",
        store=True,
        index=True,
        readonly=True,
    )
    attendance_type = fields.Selection(
        [("present", "On-site"), ("remote", "Remote")],
        string="Attendance mode",
        default="present",
        index=True,
        help=(
            "Whether participation is on-site or remote. Quorum and voting eligibility "
            "use Registration status (confirmed), not this field."
        ),
    )
    date_register = fields.Datetime(
        string="Registration date",
        help="When attendance was last confirmed (set on confirmation; optional for other flows).",
    )
    attendee_vote_ids = fields.One2many(
        "assembly.attendee.vote",
        "attendee_id",
        string="Votes by type",
        help=(
            "Stored snapshot per assembly vote type (own / delegated in-out). "
            "It is rebuilt when you generate attendees, change the assembly vote types, "
            "confirm or mark absent, when delegations change, or via “Recompute votes” "
            "on the assembly. Contact “Votes per contact” (partner.vote) is the source "
            "for own amounts; until a rebuild runs, lines here can be missing or stale."
        ),
    )
    attendee_state = fields.Selection(
        [
            ("registered", "Registered"),
            ("confirmed", "Confirmed"),
            ("absent", "Absent"),
        ],
        string="Registration status",
        default="registered",
        required=True,
        index=True,
        help=(
            "registered: on the list, not yet counted for quorum; "
            "confirmed: attended (counts for quorum); absent: did not attend."
        ),
    )
    attendance_signature = fields.Binary(
        string="Signature",
        help="Optional capture of attendance proof (e.g. on-site sign-in).",
    )
    attendance_notes = fields.Text(
        string="Attendance notes",
        help="Free-text notes for this registration (not used by core quorum logic).",
    )
    attendance_link_tracker_id = fields.Many2one(
        "link.tracker",
        string="Attendance link tracker",
        copy=False,
        ondelete="set null",
        help="link.tracker row whose target URL is GET /assembly/attendance for this row.",
    )
    attendance_url = fields.Char(
        string="Tracked attendance link (QR)",
        compute="_compute_attendance_url",
        help=(
            "Short URL from link_tracker (destination: GET /assembly/attendance with "
            "assembly_id and participant_id). For managers with a session, opening "
            "it reaches the same flow as the direct attendance link."
        ),
    )
    partner_vat = fields.Char(
        string="TIN",
        related="partner_id.vat",
        readonly=True,
    )
    total_votes = fields.Float(
        string="Total votes",
        compute="_compute_total_votes",
    )
    count_attendee_votes = fields.Integer(
        string="Vote types count",
        compute="_compute_count_attendee_votes",
    )

    @api.depends("attendee_vote_ids")
    def _compute_count_attendee_votes(self):
        for attendee in self:
            attendee.count_attendee_votes = len(attendee.attendee_vote_ids)

    @api.depends(
        "partner_id",
        "partner_id.name",
        "participant_partner_id",
        "participant_partner_id.name",
    )
    def _compute_name(self):
        for rec in self:
            if not rec.partner_id:
                rec.name = ""
                continue
            member = rec.partner_id.display_name
            if (
                rec.participant_partner_id
                and rec.participant_partner_id != rec.partner_id
            ):
                rec.name = f"{member} / {rec.participant_partner_id.display_name}"
            else:
                rec.name = member

    @api.depends("attendance_link_tracker_id", "attendance_link_tracker_id.short_url")
    def _compute_attendance_url(self):
        for rec in self:
            lt = rec.attendance_link_tracker_id
            rec.attendance_url = (lt.short_url or "") if lt else ""

    def _attendance_flow_target_url(self):
        """Absolute URL for the documented attendance entry (query: assembly_id, participant_id)."""
        self.ensure_one()
        if not self.assembly_id or not self.partner_id:
            return ""
        base = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("web.base.url", "")
            .rstrip("/")
        )
        path = (
            f"/assembly/attendance?assembly_id={self.assembly_id.id}"
            f"&participant_id={self.partner_id.id}"
        )
        if base:
            return f"{base}{path}"
        return path

    def _attendance_link_tracker_label(self):
        """Stable key for ``link.tracker.label`` (one short link per attendee row)."""
        self.ensure_one()
        return "assembly.attendee:%s" % self.id

    def _sync_attendance_link_trackers(self):
        """Bind ``link.tracker`` rows to :meth:`_attendance_flow_target_url` (GET /assembly/attendance).

        Reuses the tracker for this attendee by ``label`` so the ``/r/<code>`` path stays
        stable when only ``web.base.url`` or query parameters change; updates stored
        ``url`` / ``title`` on the tracker when needed.
        """
        link_tracker = self.env["link.tracker"].sudo()
        for rec in self:
            if not rec.id or not rec.assembly_id or not rec.partner_id:
                continue
            target = rec._attendance_flow_target_url()
            if not target:
                continue
            label = rec._attendance_link_tracker_label()
            title = self.env._("Assembly attendance — %s", rec.display_name)
            existing = link_tracker.search([("label", "=", label)], order="id", limit=1)
            if existing:
                patch = {}
                if existing.url != target:
                    patch["url"] = target
                if existing.title != title:
                    patch["title"] = title
                if patch:
                    existing.write(patch)
                if rec.attendance_link_tracker_id != existing:
                    rec.with_context(
                        assembly_attendee_skip_link_tracker_resync=True
                    ).sudo().write({"attendance_link_tracker_id": existing.id})
                continue
            trackers = link_tracker.search_or_create(
                [{"url": target, "title": title, "label": label}]
            )
            tracker = trackers[0] if trackers else False
            if tracker and rec.attendance_link_tracker_id != tracker:
                rec.with_context(
                    assembly_attendee_skip_link_tracker_resync=True
                ).sudo().write({"attendance_link_tracker_id": tracker.id})

    @api.model
    def _normalize_partner_vat_for_confirm_check(self, vat):
        return re.sub(r"[\s\-\.]", "", (vat or "").upper())

    @api.model
    def _partner_vat_passes_light_format_check(self, vat):
        normalized = self._normalize_partner_vat_for_confirm_check(vat)
        if len(normalized) < 5 or len(normalized) > 32:
            return False
        return bool(re.fullmatch(r"[A-Z0-9]+", normalized))

    @api.depends("attendee_vote_ids", "attendee_vote_ids.attendee_vote_total")
    def _compute_total_votes(self):
        for attendee in self:
            attendee.total_votes = sum(
                attendee.attendee_vote_ids.mapped("attendee_vote_total")
            )

    def action_open_attendee_votes(self):
        return self._action_window(
            "assembly.attendee.vote",
            self.env._("Votes by type"),
            "list",
            domain=[("attendee_id", "=", self.id)],
            context={"default_attendee_id": self.id},
        )

    _sql_constraints = [
        (
            "assembly_partner_uniq",
            "UNIQUE(assembly_id, partner_id)",
            "Partner can only be registered once per assembly.",
        ),
    ]

    @api.model
    def _search_attendees_for_assembly(
        self,
        assembly_id,
        *,
        partner_ids=None,
        attendee_state=None,
        limit=None,
    ):
        if not assembly_id:
            return self.browse()
        if partner_ids is not None:
            pids = list(partner_ids)
            if not pids:
                return self.browse()
            if len(pids) == 1:
                return self._search_for_assembly_partner(
                    assembly_id,
                    pids[0],
                    limit=limit,
                    attendee_state=attendee_state,
                )
        domain = [("assembly_id", "=", assembly_id)]
        if partner_ids is not None:
            domain.append(("partner_id", "in", pids))
        if attendee_state is not None:
            domain.append(("attendee_state", "=", attendee_state))
        kw = {}
        if limit is not None:
            kw["limit"] = limit
        return self.search(domain, **kw)

    @api.model
    def _search_attendees_by_assembly_partners(self, assembly_id, partner_ids):
        if not assembly_id or not partner_ids:
            return self.browse()
        return self._search_attendees_for_assembly(
            assembly_id, partner_ids=list(partner_ids)
        )

    @api.model
    def _search_for_assembly_partner(
        self, assembly_id, partner_id, limit=1, attendee_state=None
    ):
        if not assembly_id or not partner_id:
            return self.browse()
        domain = [
            ("assembly_id", "=", assembly_id),
            ("partner_id", "=", partner_id),
        ]
        if attendee_state is not None:
            domain.append(("attendee_state", "=", attendee_state))
        return self.search(domain, limit=limit)

    @api.model
    def _validate_attendee_create_initial_states(self, vals_list):
        for vals in vals_list:
            initial_state = vals.get("attendee_state", "registered")
            if initial_state not in _ATTENDEE_STATE_KEYS:
                raise UserError(
                    self.env._(
                        "Invalid registration status for new attendee: %(state)s",
                        state=initial_state,
                    )
                )
            if initial_state != "registered":
                raise UserError(
                    self.env._(
                        "New attendees must be created in registered status. "
                        "Got: %(state)s",
                        state=initial_state,
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        if not vals_list:
            return self.browse()
        vals_list = [dict(vals) for vals in vals_list]
        self._validate_attendee_create_initial_states(vals_list)
        asm_ids = {v.get("assembly_id") for v in vals_list if v.get("assembly_id")}
        if asm_ids:
            self.env["assembly.assembly"].browse(
                list(asm_ids)
            ).exists()._assembly_ensure_not_closed_for_related_changes()
        recs = super().create(vals_list)
        if not self.env.context.get("assembly_attendee_skip_link_tracker_resync"):
            recs._sync_attendance_link_trackers()
        return recs

    def _raise_disallowed_attendee_state_transition(self, old_state, new_state):
        if new_state == "confirmed":
            raise UserError(
                self.env._(
                    "Only attendees in Registered or Absent status can be confirmed."
                )
            )
        if new_state == "absent":
            raise UserError(
                self.env._(
                    "Only attendees in Registered or Confirmed status can be marked absent."
                )
            )
        raise UserError(
            self.env._(
                "Invalid registration status transition: %(old)s → %(new)s",
                old=old_state,
                new=new_state,
            )
        )

    @api.model
    def _attendee_is_allowed_registration_state_transition(self, old_state, new_state):
        """Structural allow-list for ``attendee_state`` (excluding same-state noop).

        Callers should treat ``old_state == new_state`` as valid no-op before
        calling this helper.
        """
        if (
            old_state not in _ATTENDEE_STATE_KEYS
            or new_state not in _ATTENDEE_STATE_KEYS
        ):
            return False
        return new_state in _ATTENDEE_ALLOWED_STATE_TRANSITIONS.get(
            old_state, frozenset()
        )

    def _validate_attendee_state_transition(self, old_state, new_state):
        if old_state == new_state:
            return
        if (
            old_state not in _ATTENDEE_STATE_KEYS
            or new_state not in _ATTENDEE_STATE_KEYS
        ):
            raise UserError(
                self.env._(
                    "Invalid registration status transition: %(old)s → %(new)s",
                    old=old_state,
                    new=new_state,
                )
            )
        if not self.env[
            "assembly.attendee"
        ]._attendee_is_allowed_registration_state_transition(old_state, new_state):
            self._raise_disallowed_attendee_state_transition(old_state, new_state)

    def _transition_attendee_registration_state(self, new_state, extra_vals=None):
        """Persist ``attendee_state`` via the internal write context (see :meth:`write`)."""
        self.ensure_one()
        vals = dict(extra_vals or ())
        vals["attendee_state"] = new_state
        return self.with_context(
            **{CTX_ATTENDEE_ALLOW_REGISTRATION_STATE_WRITE: True}
        ).write(vals)

    def _validate_and_sanitize_attendee_write_vals(self, vals):
        vals = dict(vals)
        if "attendee_state" in vals:
            new_state = vals["attendee_state"]
            if new_state not in _ATTENDEE_STATE_KEYS:
                raise UserError(
                    self.env._(
                        "Invalid registration status: %(state)s",
                        state=repr(new_state),
                    )
                )
            for rec in self:
                rec._validate_attendee_state_transition(rec.attendee_state, new_state)
        return vals

    def _write_would_change_assembly_or_partner(self, vals):
        """True if ``vals`` would change ``assembly_id`` or ``partner_id`` on any row."""
        if "assembly_id" not in vals and "partner_id" not in vals:
            return False
        for rec in self:
            if "assembly_id" in vals:
                new_aid = vals["assembly_id"]
                if isinstance(new_aid, models.BaseModel):
                    new_aid = new_aid.id if new_aid else False
                if rec.assembly_id.id != new_aid:
                    return True
            if "partner_id" in vals:
                new_pid = vals["partner_id"]
                if isinstance(new_pid, models.BaseModel):
                    new_pid = new_pid.id if new_pid else False
                if rec.partner_id.id != new_pid:
                    return True
        return False

    def _write_would_change_registration_state(self, vals):
        """True if ``attendee_state`` in ``vals`` differs from stored state on any row."""
        if "attendee_state" not in vals:
            return False
        new_state = vals["attendee_state"]
        return any(rec.attendee_state != new_state for rec in self)

    def write(self, vals):
        """Persist fields; **does not** recompute vote lines.

        Vote snapshots are updated only from :meth:`recompute_votes` (``action_confirm``,
        ``action_mark_absent``, ``assembly.delegation`` create/write hook).

        * ``assembly_id`` / ``partner_id`` cannot be changed on saved rows unless
          context ``assembly_attendee_allow_identity_write`` is set (import/rare).
        * ``attendee_state`` cannot be changed except through the internal context
          ``assembly_attendee_allow_registration_state_write``, which
          :meth:`_transition_attendee_registration_state` sets — use
          ``action_confirm`` / ``action_mark_absent`` in normal UI and integrations.
        """
        self.mapped("assembly_id")._assembly_ensure_not_closed_for_related_changes()
        vals = self._validate_and_sanitize_attendee_write_vals(vals)
        if self.ids:
            if self._write_would_change_assembly_or_partner(vals):
                if not self.env.context.get(CTX_ATTENDEE_ALLOW_IDENTITY_WRITE):
                    raise UserError(
                        self.env._(
                            "You cannot change the assembly or member on an existing "
                            "registration. Remove this row and add a new one instead."
                        )
                    )
            if self._write_would_change_registration_state(vals):
                if not self.env.context.get(
                    CTX_ATTENDEE_ALLOW_REGISTRATION_STATE_WRITE
                ):
                    raise UserError(
                        self.env._(
                            "Registration status cannot be changed with a generic save. "
                            "Use Confirm or Mark absent on the attendee (or the same "
                            "server actions / API those buttons call)."
                        )
                    )
        res = super().write(vals)
        if not self.env.context.get("assembly_attendee_skip_link_tracker_resync"):
            if {"assembly_id", "partner_id"} & vals.keys():
                self._sync_attendance_link_trackers()
        return res

    def unlink(self):
        self.mapped("assembly_id")._assembly_ensure_not_closed_for_related_changes()
        return super().unlink()

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id and not self.participant_partner_id:
            self.participant_partner_id = self.partner_id

    def _ensure_assembly_and_partner_for_action(
        self, *, no_assembly_msg, no_partner_msg
    ):
        self.ensure_one()
        if not self.assembly_id:
            raise ValidationError(no_assembly_msg)
        if not self.partner_id:
            raise ValidationError(no_partner_msg)

    def _validate_can_confirm(self):
        """Gate for :meth:`action_confirm` (and internal confirm path).

        * ``assembly_id.attendance_require_partner_vat_confirm``: non-empty TIN; optional
          ``attendance_partner_vat_format_strict`` (from type defaults).
        * ``assembly.assembly_type_id.require_vat``: same TIN rule with type-scoped message
          when the assembly flag above is off.
        """
        self._ensure_assembly_and_partner_for_action(
            no_assembly_msg=self.env._("Cannot confirm attendee without an assembly."),
            no_partner_msg=self.env._("Cannot confirm attendee without a partner."),
        )
        self.ensure_one()
        asm = self.assembly_id
        raw = (self.partner_id.vat or "").strip()
        atype = asm.assembly_type_id
        type_requires_vat = bool(atype and atype.require_vat)
        if asm.attendance_require_partner_vat_confirm:
            if not raw or raw == "/":
                raise ValidationError(
                    self.env._(
                        "This assembly requires a tax identification number (TIN/VAT) "
                        "on the member before attendance can be confirmed."
                    )
                )
            if asm.attendance_partner_vat_format_strict:
                Attendee = self.env["assembly.attendee"]
                if not Attendee._partner_vat_passes_light_format_check(raw):
                    raise ValidationError(
                        self.env._(
                            "The member's tax identification number (TIN/VAT) does not "
                            "meet the required format for this assembly."
                        )
                    )
        elif type_requires_vat:
            if not raw or raw == "/":
                raise ValidationError(
                    self.env._(
                        "This assembly type requires a tax identification number "
                        "(TIN/VAT) on the member before attendance can be "
                        "confirmed."
                    )
                )
            if asm.attendance_partner_vat_format_strict:
                Attendee = self.env["assembly.attendee"]
                if not Attendee._partner_vat_passes_light_format_check(raw):
                    raise ValidationError(
                        self.env._(
                            "The member's tax identification number (TIN/VAT) does "
                            "not meet the required format for this assembly."
                        )
                    )
        if asm.attendance_require_partner_vat_confirm or type_requires_vat:
            # AF v2.0 §2.5 / §4.11: use Odoo ``base_vat`` rules when TIN is required.
            self.partner_id.check_vat()

    def _apply_confirm_state(self):
        self.ensure_one()
        self._transition_attendee_registration_state(
            "confirmed", {"date_register": fields.Datetime.now()}
        )

    def _gather_delegation_effects_after_confirm(self, confirmed_delegations_pool):
        self.ensure_one()
        inbound = self._get_inbound_delegator_attendees(
            confirmed_delegations=confirmed_delegations_pool,
        )
        warning = self._get_outbound_delegation_warning_message(
            confirmed_delegations=confirmed_delegations_pool,
        )
        return inbound, warning

    def _get_confirm_result(self, warnings):
        if warnings:
            return {
                "warning": {
                    "title": self.env._("Active delegations detected"),
                    "message": "\n".join(warnings),
                    "type": "notification",
                }
            }
        return True

    @api.model
    def _confirmed_delegations_for_assemblies(self, assembly_ids):
        """All ``delegation_state == confirmed`` rows per assembly (no partner filter).

        Delegate/delegator **effectiveness** (confirmed delegate attendee, chain rules,
        etc.) is applied in :meth:`assembly.delegation._get_effective_delegations`.
        """
        Delegation = self.env["assembly.delegation"]
        aids = [int(x) for x in assembly_ids if x]
        if not aids:
            return {}
        delegations = Delegation.search(
            [
                ("assembly_id", "in", list(set(aids))),
                ("delegation_state", "=", "confirmed"),
            ]
        )
        buckets = defaultdict(list)
        for d in delegations:
            buckets[d.assembly_id.id].append(d.id)
        return {aid: Delegation.browse(ids) for aid, ids in buckets.items()}

    def _get_effective_delegations(
        self,
        role,
        *,
        confirmed_delegations_pool=None,
        for_stored_vote_lines=True,
        apply_delegate_attendee_effect=True,
    ):
        """Delegations that affect **vote** math for this member (wrapper).

        Implements the same contract as :meth:`assembly.delegation._get_effective_delegations`
        for ``(assembly_id, partner_id)`` of this row. Quorum presence uses
        :meth:`~assembly.delegation._get_effective_delegations` with ``delegations=``
        on the assembly's delegation rows (partner layer only).
        """
        self.ensure_one()
        Delegation = self.env["assembly.delegation"]
        if (
            not self.assembly_id
            or not self.partner_id
            or role not in ("delegator", "delegate")
        ):
            return Delegation.browse()
        return Delegation._get_effective_delegations(
            self.assembly_id.id,
            self.partner_id.id,
            role,
            confirmed_delegations_pool=confirmed_delegations_pool,
            for_stored_vote_lines=for_stored_vote_lines,
            apply_delegate_attendee_effect=apply_delegate_attendee_effect,
            member_attendee=self,
        )

    def _get_inbound_delegator_attendees(self, confirmed_delegations=None):
        self.ensure_one()
        delegations = self._get_effective_delegations(
            "delegate",
            confirmed_delegations_pool=confirmed_delegations,
            for_stored_vote_lines=False,
        )
        if not delegations:
            return self.env["assembly.attendee"]
        return self.env["assembly.attendee"]._search_attendees_by_assembly_partners(
            self.assembly_id.id,
            delegations.mapped("partner_id").ids,
        )

    def _get_outbound_delegation_warning_message(self, confirmed_delegations=None):
        self.ensure_one()
        active = self._get_effective_delegations(
            "delegator",
            confirmed_delegations_pool=confirmed_delegations,
            for_stored_vote_lines=False,
        )
        if not active:
            return ""
        delegate_names = ", ".join(active.mapped("delegate_partner_id.name"))
        return self.env._(
            "%(partner)s has %(count)d active confirmed delegation(s) "
            "to: %(delegates)s. These delegations remain active and "
            "have not been revoked. "
            "You can revoke them manually if needed.",
            partner=self.partner_id.name,
            count=len(active),
            delegates=delegate_names,
        )

    def _confirm_attendee_and_gather_delegation_effects(
        self, confirmed_delegations_pool
    ):
        self.ensure_one()
        self._validate_attendee_state_transition(self.attendee_state, "confirmed")
        self._validate_can_confirm()
        self._apply_confirm_state()
        return self._gather_delegation_effects_after_confirm(confirmed_delegations_pool)

    def action_confirm(self):
        confirmed_in_action = self.env["assembly.attendee"]
        delegators_to_recompute = self.env["assembly.attendee"]
        delegates_outbound_touch = self.env["assembly.attendee"]
        warnings = []
        delegations_by_assembly = self._confirmed_delegations_for_assemblies(
            self.mapped("assembly_id").ids
        )
        Delegation = self.env["assembly.delegation"]
        Attendee = self.env["assembly.attendee"]
        for rec in self:
            if rec.attendee_state == "confirmed":
                continue
            pool = delegations_by_assembly.get(rec.assembly_id.id, Delegation.browse())
            inbound, msg = rec._confirm_attendee_and_gather_delegation_effects(pool)
            confirmed_in_action |= rec
            delegators_to_recompute |= inbound
            outbound = rec._get_effective_delegations(
                "delegator",
                confirmed_delegations_pool=pool,
            )
            if outbound:
                delegates_outbound_touch |= (
                    Attendee._search_attendees_by_assembly_partners(
                        rec.assembly_id.id,
                        outbound.mapped("delegate_partner_id").ids,
                    )
                )
            if msg:
                warnings.append(msg)
        to_recompute = (
            confirmed_in_action | delegators_to_recompute | delegates_outbound_touch
        )
        self.env["assembly.attendee"].recompute_votes(to_recompute)
        return self._get_confirm_result(warnings)

    def _validate_can_mark_absent(self):
        self._ensure_assembly_and_partner_for_action(
            no_assembly_msg=self.env._(
                "Cannot mark attendee absent without an assembly."
            ),
            no_partner_msg=self.env._("Cannot mark attendee absent without a partner."),
        )
        open_cast = self.env["assembly.voting.line"].search(
            [
                ("attendee_id", "=", self.id),
                ("vote_option", "!=", "unset"),
                ("voting_id.voting_state", "=", "open"),
            ],
            limit=1,
        )
        if open_cast:
            raise UserError(
                self.env._(
                    "This member has already cast a vote in an open roll-call voting. "
                    "Cancel or close that voting (or clear the vote line) before "
                    "marking them absent."
                )
            )

    def _apply_absent_state(self):
        self.ensure_one()
        previous = self.attendee_state
        self._transition_attendee_registration_state("absent")
        return previous

    def _mark_attendee_absent_and_collect_recompute_targets(self):
        self.ensure_one()
        self._validate_attendee_state_transition(self.attendee_state, "absent")
        self._validate_can_mark_absent()
        previous_state = self._apply_absent_state()
        affected = self.env["assembly.attendee"]
        if previous_state == "confirmed":
            affected = self._attendees_affected_by_delegations_when_leaving_confirmed()
        return self | affected

    def _attendees_affected_by_delegations_when_leaving_confirmed(self):
        self.ensure_one()
        Attendee = self.env["assembly.attendee"]
        affected = Attendee.browse()
        aid = self.assembly_id.id
        delegations_in = self._get_effective_delegations(
            "delegate",
            for_stored_vote_lines=False,
            apply_delegate_attendee_effect=False,
        )
        if delegations_in:
            affected |= Attendee._search_attendees_by_assembly_partners(
                aid,
                delegations_in.mapped("partner_id").ids,
            )
        delegations_out = self._get_effective_delegations(
            "delegator",
            for_stored_vote_lines=False,
            apply_delegate_attendee_effect=False,
        )
        if delegations_out:
            affected |= Attendee._search_attendees_by_assembly_partners(
                aid,
                delegations_out.mapped("delegate_partner_id").ids,
            )
        return affected

    def action_mark_absent(self):
        attendees_to_recompute = self.env["assembly.attendee"]
        for rec in self:
            if rec.attendee_state == "absent":
                continue
            attendees_to_recompute |= (
                rec._mark_attendee_absent_and_collect_recompute_targets()
            )
        if attendees_to_recompute:
            self.env["assembly.attendee"].recompute_votes(attendees_to_recompute)

    @api.model
    def recompute_votes(self, attendees):
        """Rebuild stored ``assembly.attendee.vote`` for ``attendees`` (public API).

        **Only supported batch entry point** for vote snapshots. Internal work is done
        by :meth:`_recompute_votes_for_recordset` (do not call it from other modules).

        **Only these business flows invoke this method (no implicit hooks elsewhere):**

        * :meth:`action_confirm`, :meth:`action_mark_absent`
        * ``assembly.delegation`` ``create`` / ``write`` (post-persist hook)
        * :meth:`~assembly.assembly.action_generate_attendees` (all attendees on that assembly)
        * ``assembly.assembly.write`` when ``vote_type_ids`` is updated

        Raises ``UserError`` if any related assembly is ``closed`` (same rule as
        other child mutations).

        Changing other assembly fields does **not** trigger a recompute. If
        ``partner.vote`` rows change after the last rebuild, use “Recompute votes”
        on the assembly (or call this method).

        **Computation:** each attendee snapshot is rebuilt from ``partner.vote``,
        assembly vote types, and effective delegations — not from previous values
        on ``assembly.attendee.vote`` rows (existing rows are updated or removed
        only as persistence targets; :meth:`_cleanup_obsolete_attendee_vote_rows`
        drops types no longer on the assembly).

        **Properties:** idempotent; order-independent (per assembly, sorted ids).

        ``assembly.attendee.write`` does **not** invoke this method. Context flags
        on ``write`` only guard identity / registration fields, not vote recompute.
        """
        if not attendees:
            return
        attendees = attendees.exists()
        if not attendees:
            return
        assemblies = attendees.mapped("assembly_id").exists()
        assemblies._assembly_ensure_not_closed_for_related_changes()
        Attendee = self.env["assembly.attendee"]
        by_assembly = defaultdict(list)
        for attendee in attendees:
            if not attendee.assembly_id:
                continue
            by_assembly[attendee.assembly_id.id].append(attendee.id)
        for aid in sorted(by_assembly):
            unique_ids = sorted(set(by_assembly[aid]))
            Attendee.browse(unique_ids)._recompute_votes_for_recordset()

    def recompute_attendee_vote_lines(self):
        """Backward-compatible alias for :meth:`recompute_votes` on this recordset."""
        return self.env["assembly.attendee"].recompute_votes(self)

    @api.model
    def _calculate_base_votes(self, partner, vote_types):
        if not partner or not vote_types:
            return {}
        PartnerVote = self.env["partner.vote"]
        pvs = PartnerVote.search(
            [
                ("partner_id", "=", partner.id),
                ("vote_type_id", "in", vote_types.ids),
            ],
            order="id",
        )
        by_type_id = {}
        for pv in pvs:
            vt_id = pv.vote_type_id.id
            if vt_id not in by_type_id:
                by_type_id[vt_id] = pv.vote_count_display
        return by_type_id

    @api.model
    def _delegation_applies_to_vote_type(self, delegation, vote_type):
        """Whether ``vote_type`` is in this delegation's expanded coverage (vote math only)."""
        return delegation.delegation_covers_vote_type(vote_type)

    @api.model
    def _apply_delegated_out(self, effective_out, vote_type, base_own_votes):
        """Amount delegated **out**: only this partner's ``partner.vote`` for the type.

        ``base_own_votes`` must come from :meth:`_calculate_base_votes` (never totals
        nor ``delegated_in``). Vote chaining is also blocked on delegations
        (ORM validation and ``assembly.delegation._exclude_outbound_vote_chain_overlap``).
        """
        if not effective_out:
            return 0.0
        base = max(0.0, float(base_own_votes))
        if base <= 0.0:
            return 0.0
        if not any(
            self._delegation_applies_to_vote_type(d, vote_type) for d in effective_out
        ):
            return 0.0
        return base

    @api.model
    def _apply_delegated_in(
        self,
        effective_in,
        vote_type,
        *,
        pv_by_partner_and_type=None,
    ):
        if not effective_in:
            return 0.0
        delegations = effective_in.filtered(
            lambda d, st=self: st._delegation_applies_to_vote_type(d, vote_type)
        ).sorted("id")
        if not delegations:
            return 0.0
        if pv_by_partner_and_type:
            return self._sum_delegators_own_votes_prefetched(
                delegations, vote_type, pv_by_partner_and_type
            )
        return self._sum_delegators_own_votes_from_search(delegations, vote_type)

    @api.model
    def _sum_delegators_own_votes_prefetched(
        self, delegations, vote_type, pv_by_partner_and_type
    ):
        """Sum delegators' **own** entitlement from ``partner.vote`` only.

        Never uses ``assembly.attendee.vote`` (avoids counting ``delegated_in``
        of the delegator). Delegators without an attendee row still contribute
        via their ``partner.vote`` rows.

        If the prefetch map omits a (partner, vote type) pair, falls back to a
        direct ``partner.vote`` search so non-attendee delegators stay correct
        and deterministic (same rule as ``_sum_delegators_own_votes_from_search``).
        """
        total = 0.0
        vt_id = vote_type.id
        PartnerVote = self.env["partner.vote"]
        delegations = delegations.sorted("id")
        missing_fetch = []
        for delegation in delegations:
            pid = delegation.partner_id.id
            inner = pv_by_partner_and_type.get(pid)
            if inner and vt_id in inner:
                total += inner[vt_id]
            else:
                missing_fetch.append((delegation, pid))
        if missing_fetch:
            pids = list({pid for __, pid in missing_fetch})
            pvs = PartnerVote.search(
                [
                    ("partner_id", "in", pids),
                    ("vote_type_id", "=", vt_id),
                ],
                order="id",
            )
            by_pid = {}
            for pv in pvs:
                opid = pv.partner_id.id
                if opid not in by_pid:
                    by_pid[opid] = pv.vote_count_display
            for __, pid in missing_fetch:
                total += by_pid.get(pid, 0.0)
        return total

    @api.model
    def _sum_delegators_own_votes_from_search(self, delegations, vote_type):
        """Sum ``partner.vote`` for each delegator partner (own votes only)."""
        partner_ids = delegations.mapped("partner_id").ids
        PartnerVote = self.env["partner.vote"]
        pvs = PartnerVote.search(
            [
                ("partner_id", "in", partner_ids),
                ("vote_type_id", "=", vote_type.id),
            ],
            order="id",
        )
        pv_by_partner_id = {}
        for pv in pvs:
            pid = pv.partner_id.id
            if pid not in pv_by_partner_id:
                pv_by_partner_id[pid] = pv
        total = 0.0
        for delegation in delegations.sorted("id"):
            pv = pv_by_partner_id.get(delegation.partner_id.id)
            if pv:
                total += pv.vote_count_display
        return total

    @api.model
    def _collapse_duplicate_attendee_vote_lines(self, line_recordset):
        """Keep a single row per ``(attendee_id, vote_type_id)`` (lowest ``id``).

        Used before/during vote persistence so recomputation always targets one row
        per pair. Safe on empty or singleton recordsets.
        """
        sudo_lines = line_recordset.sudo()
        if len(sudo_lines) <= 1:
            return sudo_lines
        by_pair = defaultdict(list)
        for line in sudo_lines:
            by_pair[(line.attendee_id.id, line.vote_type_id.id)].append(line)
        extras = sudo_lines.browse()
        for lines in by_pair.values():
            lines.sort(key=lambda r: r.id)
            for dup in lines[1:]:
                extras |= dup
        if extras:
            extras.unlink()
        return sudo_lines - extras

    def _prefetch_and_dedupe_attendee_vote_lines(self, attendee_ids, vote_type_ids):
        """Load existing vote lines for the batch and collapse duplicates into a map."""
        AttendeeVote = self.env["assembly.attendee.vote"]
        line_by_pair = {}
        aids = [int(x) for x in attendee_ids if x]
        vtids = [int(x) for x in vote_type_ids if x]
        if not aids or not vtids:
            return line_by_pair
        AttendeeVote.flush_model()
        prefetched = AttendeeVote.sudo().search(
            [
                ("attendee_id", "in", aids),
                ("vote_type_id", "in", vtids),
            ],
            order="id",
        )
        clean = self._collapse_duplicate_attendee_vote_lines(prefetched)
        for line in clean.sorted(
            key=lambda rec: (rec.attendee_id.id, rec.vote_type_id.id, rec.id)
        ):
            k = (line.attendee_id.id, line.vote_type_id.id)
            line_by_pair[k] = line
        return line_by_pair

    def _fetch_unique_vote_line_for_type(self, vote_type, line_by_pair=None):
        """Return 0 or 1 ``assembly.attendee.vote`` for this attendee and vote type.

        Prefers ``line_by_pair`` when still valid; otherwise search, collapse
        duplicates, and refresh the map. Flushes so concurrent writes are visible.
        """
        self.ensure_one()
        key = (self.id, vote_type.id)
        if line_by_pair is not None:
            cached = line_by_pair.get(key)
            if cached and cached.exists():
                return cached
        AttendeeVote = self.env["assembly.attendee.vote"]
        AttendeeVote.flush_model()
        domain = [
            ("attendee_id", "=", self.id),
            ("vote_type_id", "=", vote_type.id),
        ]
        found = AttendeeVote.sudo().search(domain, order="id")
        if len(found) > 1:
            self.env["assembly.attendee"]._collapse_duplicate_attendee_vote_lines(found)
            found = AttendeeVote.sudo().search(domain, order="id")
        existing = found[:1]
        if line_by_pair is not None:
            if existing:
                line_by_pair[key] = existing
            else:
                line_by_pair.pop(key, None)
        return existing

    def _ensure_non_negative_vote_components(
        self, attendee, vote_type, own_votes, delegated_out_votes, delegated_in_votes
    ):
        checks = (
            (
                own_votes < 0.0,
                "Own votes cannot be negative (attendee %(attendee)s, type %(vtype)s).",
            ),
            (
                delegated_out_votes < 0.0,
                "Delegated out votes cannot be negative (attendee %(attendee)s, type %(vtype)s).",
            ),
            (
                delegated_in_votes < 0.0,
                "Delegated in votes cannot be negative (attendee %(attendee)s, type %(vtype)s).",
            ),
        )
        for bad, msg in checks:
            if bad:
                raise ValidationError(
                    self.env._(
                        msg,
                        attendee=attendee.id,
                        vtype=vote_type.id,
                    )
                )

    def _persist_attendee_vote_line(
        self,
        vote_type,
        own_votes,
        delegated_out_votes,
        delegated_in_votes,
        *,
        line_by_pair=None,
    ):
        """Persist one snapshot row: **update** if present else **create** (idempotent).

        Uniqueness: SQL ``UNIQUE(attendee_id, vote_type_id)`` and
        :meth:`_fetch_unique_vote_line_for_type` / :meth:`_collapse_duplicate_attendee_vote_lines`.
        Repeated recomputation only updates the same logical row via ``write``.
        ``IntegrityError`` (concurrent insert) → fetch, collapse, ``write``.
        """
        self.ensure_one()
        self._ensure_non_negative_vote_components(
            self,
            vote_type,
            own_votes,
            delegated_out_votes,
            delegated_in_votes,
        )
        AttendeeVote = self.env["assembly.attendee.vote"]
        vals = {
            "own_votes": own_votes,
            "delegated_out_votes": delegated_out_votes,
            "delegated_in_votes": delegated_in_votes,
        }
        key = (self.id, vote_type.id)
        existing = self._fetch_unique_vote_line_for_type(
            vote_type, line_by_pair=line_by_pair
        )
        if existing:
            existing.sudo().write(vals)
            if line_by_pair is not None:
                line_by_pair[key] = existing
            return
        with self.env.cr.savepoint():
            try:
                created = AttendeeVote.sudo().create(
                    {
                        "attendee_id": self.id,
                        "vote_type_id": vote_type.id,
                        **vals,
                    }
                )
            except IntegrityError as exc:
                if getattr(exc, "pgcode", None) != errorcodes.UNIQUE_VIOLATION:
                    raise
                existing = self._fetch_unique_vote_line_for_type(
                    vote_type, line_by_pair=line_by_pair
                )
                if not existing:
                    raise RuntimeError(
                        "assembly.attendee.vote unique conflict but no row found "
                        f"for attendee={self.id}, vote_type={vote_type.id}"
                    ) from exc
                existing.sudo().write(vals)
                if line_by_pair is not None:
                    line_by_pair[key] = existing
            else:
                if line_by_pair is not None:
                    line_by_pair[key] = created

    @api.model
    def _prefetch_delegator_partner_votes_map(self, effective_in, vote_types):
        if not effective_in:
            return None
        PartnerVote = self.env["partner.vote"]
        delegator_pids = effective_in.mapped("partner_id").ids
        pv_by_partner_and_type = defaultdict(dict)
        for pv in PartnerVote.search(
            [
                ("partner_id", "in", delegator_pids),
                ("vote_type_id", "in", vote_types.ids),
            ],
            order="id",
        ):
            pid, vt_id = pv.partner_id.id, pv.vote_type_id.id
            if vt_id not in pv_by_partner_and_type[pid]:
                pv_by_partner_and_type[pid][vt_id] = pv.vote_count_display
        return pv_by_partner_and_type

    def _build_vote_line_rows_for_attendee_snapshot(
        self,
        vote_types,
        own_by_type,
        confirmed,
        effective_out,
        effective_in,
        pv_by_partner_and_type,
    ):
        """Build component dicts; ``vote_types`` must already be in deterministic order.

        No chaining: ``delegated_out_votes`` uses only ``own_by_type`` (``partner.vote``).
        ``delegated_in_votes`` sums each inbound delegator's ``partner.vote`` for the
        type (see :meth:`_apply_delegated_in`), never stored inbound of intermediaries.
        """
        rows = {}
        for vote_type in vote_types:
            base_own_votes = own_by_type.get(vote_type.id, 0.0)
            if confirmed:
                d_out = self._apply_delegated_out(
                    effective_out, vote_type, base_own_votes
                )
                d_out = min(max(0.0, float(base_own_votes)), d_out)
                d_in = self._apply_delegated_in(
                    effective_in,
                    vote_type,
                    pv_by_partner_and_type=pv_by_partner_and_type,
                )
            else:
                d_out, d_in = 0.0, 0.0
            rows[vote_type.id] = {
                "own_votes": base_own_votes,
                "delegated_out_votes": d_out,
                "delegated_in_votes": d_in,
            }
        return rows

    def _get_vote_recompute_inputs(self):
        """Phase 1: assembly vote types, base ``partner.vote``, effective delegations.

        Inbound ``delegated_in`` for a delegate sums each effective inbound delegator's
        **own** entitlement from ``partner.vote`` only (:meth:`_apply_delegated_in`).
        A delegator does not need an ``assembly.attendee`` row; their stored
        ``assembly.attendee.vote`` is never read for that sum.

        Returns:

        * ``None`` — no assembly; caller skips.
        * ``{"clear_lines": True}`` — assembly has no vote types; unlink all lines.
        * Otherwise a dict with ``vote_types``, ``own_by_type``, ``confirmed``,
          ``effective_out``, ``effective_in``, ``pv_map`` (optional prefetch map).
        """
        self.ensure_one()
        assembly = self.assembly_id
        if not assembly:
            return None
        vote_types = assembly.vote_type_ids.sorted("id")
        if not vote_types:
            return {"clear_lines": True}
        own_by_type = self._calculate_base_votes(self.partner_id, vote_types)
        confirmed = self.attendee_state == "confirmed"
        Delegation = self.env["assembly.delegation"]
        if confirmed:
            effective_out = self._get_effective_delegations("delegator").sorted("id")
            effective_in = self._get_effective_delegations("delegate").sorted("id")
        else:
            effective_out = effective_in = Delegation.browse()
        pv_map = None
        if confirmed and effective_in:
            pv_map = self._prefetch_delegator_partner_votes_map(
                effective_in, vote_types
            )
            if not pv_map:
                pv_map = None
        return {
            "vote_types": vote_types,
            "own_by_type": own_by_type,
            "confirmed": confirmed,
            "effective_out": effective_out,
            "effective_in": effective_in,
            "pv_map": pv_map,
        }

    def _compute_vote_components(self, inputs):
        """Phase 2: snapshot dict ``vote_type.id → {own, delegated_out, delegated_in}``."""
        return self._build_vote_line_rows_for_attendee_snapshot(
            inputs["vote_types"],
            inputs["own_by_type"],
            inputs["confirmed"],
            inputs["effective_out"],
            inputs["effective_in"],
            inputs["pv_map"],
        )

    def _persist_attendee_vote_rows(self, vote_types, rows, line_by_pair):
        """Phase 3: upsert stored lines (update-first; create only when missing)."""
        for vote_type in vote_types:
            comps = rows[vote_type.id]
            self._persist_attendee_vote_line(
                vote_type,
                comps["own_votes"],
                comps["delegated_out_votes"],
                comps["delegated_in_votes"],
                line_by_pair=line_by_pair,
            )

    def _cleanup_obsolete_attendee_vote_rows(self, current_vote_types):
        """Phase 4: remove stored lines whose vote type left the assembly.

        Uses a DB search (not ``attendee_vote_ids``) so obsolete detection is not
        tied to one2many cache; only ``vote_type_id`` membership is read, never
        stored vote magnitudes.
        """
        self.ensure_one()
        AttendeeVote = self.env["assembly.attendee.vote"]
        AttendeeVote.flush_model()
        existing_lines = AttendeeVote.sudo().search([("attendee_id", "=", self.id)])
        existing_types = existing_lines.mapped("vote_type_id")
        obsolete = existing_types - current_vote_types
        if not obsolete:
            return
        AttendeeVote.sudo().search(
            [
                ("attendee_id", "=", self.id),
                ("vote_type_id", "in", obsolete.ids),
            ]
        ).unlink()

    def _recompute_votes_core(self, line_by_pair):
        """Full snapshot recompute: inputs from domain data only; ``line_by_pair`` is write-target map."""
        self.ensure_one()
        inputs = self._get_vote_recompute_inputs()
        if inputs is None:
            return
        if inputs.get("clear_lines"):
            AttendeeVote = self.env["assembly.attendee.vote"]
            AttendeeVote.flush_model()
            AttendeeVote.sudo().search([("attendee_id", "=", self.id)]).unlink()
            return
        rows = self._compute_vote_components(inputs)
        vote_types = inputs["vote_types"]
        self._persist_attendee_vote_rows(vote_types, rows, line_by_pair)
        self._cleanup_obsolete_attendee_vote_rows(vote_types)

    def _recompute_votes_for_recordset(self):
        """Internal batch implementation; call only from :meth:`recompute_votes`.

        Each attendee gets a full snapshot (vote types and delegations sorted by
        ``id``). Shared ``line_by_pair`` map prevents duplicate rows across the batch.
        """
        if not self:
            return
        assemblies = self.mapped("assembly_id")
        if not assemblies:
            return
        vote_type_id_union = sorted(
            {vt.id for asm in assemblies for vt in asm.vote_type_ids}
        )
        line_by_pair = self._prefetch_and_dedupe_attendee_vote_lines(
            self.ids, vote_type_id_union
        )
        attendees_ordered = self.sorted(
            key=lambda att: (att.assembly_id.id or 0, att.id)
        )
        for attendee in attendees_ordered:
            attendee._recompute_votes_core(line_by_pair)
