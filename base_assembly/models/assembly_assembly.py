# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import math

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval

_DOMAIN_OPERATORS = frozenset(("&", "|", "!"))

_ASSEMBLY_STATE_KEYS = frozenset(
    {"draft", "announced", "open", "in_session", "closed", "cancelled"}
)

# Forward lifecycle (one step at a time).
_ASSEMBLY_SEQUENTIAL_TRANSITIONS = frozenset(
    {
        ("draft", "announced"),
        ("announced", "open"),
        ("open", "in_session"),
        ("in_session", "closed"),
    }
)

# Full allow-list: sequential edges + cancel from any state + reopen from cancelled.
_ASSEMBLY_ALLOWED_STATE_TRANSITIONS = frozenset(
    set(_ASSEMBLY_SEQUENTIAL_TRANSITIONS)
    | {(s, "cancelled") for s in _ASSEMBLY_STATE_KEYS}
    | {("cancelled", "draft")}
)

_ASSEMBLY_STATES_ALLOW_GENERATE_ATTENDEES = frozenset(("draft", "announced", "open"))

# Set on ``assembly.assembly`` writes that cascade to related models while the
# assembly row still reads ``closed`` (e.g. cancel → close open votings).
CTX_ASSEMBLY_INTERNAL_TRANSITION = "assembly_internal_transition"


def _eval_partner_domain_text(partner_domain_text):
    try:
        raw = safe_eval(partner_domain_text or "[]", {"__builtins__": {}})
    except (TypeError, ValueError, SyntaxError, MemoryError):
        return []
    if isinstance(raw, tuple):
        raw = list(raw)
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if isinstance(item, str) and item in _DOMAIN_OPERATORS:
            out.append(item)
        elif isinstance(item, (list, tuple)) and len(item) == 3:
            out.append(tuple(item))
        else:
            return []
    return out


def _quorum_present_percentage(present, possible):
    """Person-based attendance ratio (%) for stored ``quorum_percentage`` and rules."""
    if possible <= 0:
        return 0.0
    return present / possible * 100.0


class AssemblyAssembly(models.Model):  # pylint: disable=too-many-public-methods
    """Assembly lifecycle, quorum (stored), convocation.

    **Quorum “present people” (single source):** distinct ``res.partner`` ids for the
    assembly come only from :meth:`_get_present_partner_ids` (confirmed attendees plus
    represented delegators in the convocation domain). Stored
    ``total_present_attendees``, ``quorum_percentage``, and ``quorum_reached`` in
    :meth:`_compute_quorum` are derived solely from that set and from
    ``_get_possible_attendees_count`` — never from vote weights or stored vote lines.
    """

    _name = "assembly.assembly"
    _inherit = ["assembly.mixin.window_action"]
    _description = "Assembly"
    _order = "date_first_call desc, id desc"

    _sql_constraints = [
        (
            "assembly_code_uniq",
            "UNIQUE(code)",
            "The assembly reference code must be unique.",
        ),
    ]

    name = fields.Char(required=True)
    code = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: self.env._("New"),
    )
    assembly_type_id = fields.Many2one(
        "assembly.type",
        string="Assembly type",
        ondelete="restrict",
    )
    date_announcement = fields.Date(string="Announcement date")
    date_first_call = fields.Datetime(string="First call", index=True)
    date_second_call = fields.Datetime(string="Second call")
    date_start = fields.Datetime(string="Session start")
    date_end = fields.Datetime(string="Session end")
    location = fields.Char(
        help="Short venue label (e.g. room or building) for headers; use address "
        "fields for postal details in documents.",
    )
    street = fields.Char()
    city = fields.Char()
    zip = fields.Char(string="ZIP")
    state_id = fields.Many2one(
        "res.country.state", string="State/Province", ondelete="restrict"
    )
    country_id = fields.Many2one("res.country", string="Country", ondelete="restrict")
    president_id = fields.Many2one(
        "res.users",
        string="President",
        ondelete="set null",
    )
    secretary_id = fields.Many2one(
        "res.users",
        string="Secretary",
        ondelete="set null",
    )
    description = fields.Html(string="Convocation text")
    assembly_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("announced", "Announced"),
            ("open", "Registration open"),
            ("in_session", "In session"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        index=True,
    )
    vote_type_ids = fields.Many2many(
        "vote.type",
        "assembly_assembly_vote_type_rel",
        "assembly_id",
        "vote_type_id",
        string="Vote types",
        domain=[("active", "=", True)],
    )
    quorum_type = fields.Selection(
        [("percentage", "Percentage"), ("fixed", "Fixed number")],
        string="Quorum (1st call)",
        default="percentage",
    )
    quorum_value = fields.Float(string="Quorum value (1st call)", default=50.0)
    quorum_second_call_type = fields.Selection(
        [
            ("percentage", "Percentage"),
            ("fixed", "Fixed number"),
            ("any", "Any"),
        ],
        string="Quorum (2nd call)",
        default="any",
    )
    quorum_second_call_value = fields.Float(
        string="Quorum value (2nd call)", default=0.0
    )
    is_second_call = fields.Boolean(
        string="Held in 2nd call",
        default=False,
        help="When set, quorum rules use the second-call type/value instead of the "
        "first-call ones.",
    )
    allow_online_voting = fields.Boolean(
        string="Allow online voting",
        default=False,
        help=(
            "When enabled, eligible portal users may cast votes through the website "
            "for open votings of this assembly (subject to portal routes)."
        ),
    )
    partner_domain = fields.Text(
        string="Partner domain",
        default="[]",
        help="Odoo domain (list/tuple form, as text) on res.partner defining who may "
        "be convoked; evaluated server-side with safe_eval. Invalid text is treated "
        "as an empty domain.",
    )
    agenda_ids = fields.One2many(
        "assembly.agenda",
        "assembly_id",
        string="Agenda",
        copy=True,
    )
    attendee_ids = fields.One2many(
        "assembly.attendee",
        "assembly_id",
        string="Attendees",
    )
    delegation_ids = fields.One2many(
        "assembly.delegation",
        "assembly_id",
        string="Delegations",
    )
    total_possible_attendees = fields.Integer(
        string="Possible attendees",
        compute="_compute_quorum",
        store=True,
    )
    total_present_attendees = fields.Integer(
        string="Present attendees",
        compute="_compute_quorum",
        store=True,
    )
    quorum_reached = fields.Boolean(
        compute="_compute_quorum",
        store=True,
    )
    quorum_percentage = fields.Float(
        compute="_compute_quorum",
        store=True,
    )
    active = fields.Boolean(default=True, index=True)
    count_agenda_items = fields.Integer(
        string="Agenda items",
        compute="_compute_counts",
    )
    count_delegations = fields.Integer(
        string="Delegations count",
        compute="_compute_counts",
    )
    voting_sessions_count = fields.Integer(
        string="Voting sessions",
        compute="_compute_counts",
        help="Number of assembly.voting records linked to this assembly's agenda.",
    )
    kanban_open_votings_count = fields.Integer(
        string="Open votings (Kanban)",
        compute="_compute_kanban_vote_digest",
    )
    kanban_closed_votings_count = fields.Integer(
        string="Closed votings (Kanban)",
        compute="_compute_kanban_vote_digest",
    )
    kanban_avg_participation = fields.Float(
        string="Avg. participation (closed)",
        compute="_compute_kanban_vote_digest",
        digits=(16, 2),
    )
    kanban_results_summary = fields.Char(
        string="Results summary",
        compute="_compute_kanban_vote_digest",
    )

    @api.depends("agenda_ids", "delegation_ids", "agenda_ids.voting_ids")
    def _compute_counts(self):
        for assembly in self:
            assembly.count_agenda_items = len(assembly.agenda_ids)
            assembly.count_delegations = len(assembly.delegation_ids)
            assembly.voting_sessions_count = len(
                assembly.agenda_ids.mapped("voting_ids")
            )

    @api.depends(
        "agenda_ids.voting_ids",
        "agenda_ids.voting_ids.voting_state",
        "agenda_ids.voting_ids.participation_percentage",
        "agenda_ids.voting_ids.date_close",
        "agenda_ids.voting_ids.result_ids",
        "agenda_ids.voting_ids.result_ids.vote_option",
        "agenda_ids.voting_ids.result_ids.total_votes",
        "agenda_ids.voting_ids.result_ids.result_percentage",
    )
    def _compute_kanban_vote_digest(self):
        for asm in self:
            votings = asm.agenda_ids.mapped("voting_ids")
            asm.kanban_open_votings_count = len(
                votings.filtered(lambda v: v.voting_state == "open")
            )
            closed_v = votings.filtered(lambda v: v.voting_state == "closed")
            asm.kanban_closed_votings_count = len(closed_v)
            if closed_v:
                asm.kanban_avg_participation = sum(
                    closed_v.mapped("participation_percentage")
                ) / len(closed_v)
            else:
                asm.kanban_avg_participation = 0.0
            summary = ""
            voting_result = self.env["assembly.voting.result"]
            opt_labels = dict(
                voting_result._fields["vote_option"]._description_selection(self.env)
            )
            for voting in closed_v.sorted("date_close", reverse=True):
                scored = voting.result_ids.filtered(
                    lambda r: r.vote_option
                    in ("yes", "no", "abstention", "blank", "not_cast")
                )
                if not scored:
                    continue
                best = max(scored, key=lambda r: r.total_votes or 0.0)
                label = opt_labels.get(best.vote_option, best.vote_option)
                summary = "%s: %.1f%%" % (label, best.result_percentage or 0.0)
                break
            asm.kanban_results_summary = summary

    @api.depends(
        "partner_domain",
        "assembly_state",
        "attendee_ids",
        "attendee_ids.attendee_state",
        "attendee_ids.partner_id",
        "delegation_ids",
        "delegation_ids.delegation_state",
        "delegation_ids.partner_id",
        "delegation_ids.delegate_partner_id",
        "quorum_type",
        "quorum_value",
        "quorum_second_call_type",
        "quorum_second_call_value",
        "is_second_call",
    )
    def _compute_quorum(self):
        if self.ids:
            self.fetch(
                ["attendee_ids", "delegation_ids", "partner_domain", "assembly_state"]
            )
        # Quorum: DISTINCT people in convocation who are confirmed and/or represented
        # by a quorum-effective delegation. Does not depend on ``partner.vote``,
        # ``assembly.attendee.vote``, vote types, or any vote totals (@api.depends
        # above must stay free of those models).
        for assembly in self:
            possible = assembly._get_possible_attendees_count()
            present_partner_ids = assembly._get_present_partner_ids()
            present = len(present_partner_ids)
            assembly.total_possible_attendees = possible
            assembly.total_present_attendees = present
            if assembly.assembly_state == "cancelled" or possible <= 0:
                assembly.quorum_percentage = 0.0
                assembly.quorum_reached = False
            else:
                pct = _quorum_present_percentage(present, possible)
                assembly.quorum_percentage = pct
                assembly.quorum_reached = assembly._is_quorum_reached(
                    present_partner_ids, possible, quorum_percentage=pct
                )

    @api.onchange("assembly_type_id")
    def _onchange_assembly_type_id(self):
        if self.assembly_type_id:
            t = self.assembly_type_id
            self.vote_type_ids = t.vote_type_ids
            self.quorum_type = t.default_quorum_type
            self.quorum_value = t.default_quorum_value
            self.quorum_second_call_type = t.default_quorum_second_call_type
            self.quorum_second_call_value = t.default_quorum_second_call_value
            self.partner_domain = t.partner_domain or "[]"
            self.street = t.default_street
            self.city = t.default_city
            self.zip = t.default_zip
            self.state_id = t.default_state_id
            self.country_id = t.default_country_id
            self.president_id = t.default_president_id
            self.secretary_id = t.default_secretary_id

    def _get_partner_domain(self):
        self.ensure_one()
        return _eval_partner_domain_text(self.partner_domain)

    @api.model
    def _assembly_create_field_default(self, field_name):
        """Default value for ``field_name`` on a new assembly (for create inherit checks)."""
        field = self._fields[field_name]
        default = field.default
        if default is None:
            return None
        if callable(default):
            return default(self)
        return default

    @api.model
    def _create_vals_matches_assembly_field_default(self, field_name, vals):
        """Whether ``vals[field_name]`` is absent or still the model field default.

        Web create often sends all columns with model defaults; then
        :meth:`_apply_assembly_type_to_create_vals` must still copy the type (AF §2.2).
        """
        if field_name not in vals:
            return True
        field = self._fields[field_name]
        val = vals[field_name]
        default = self._assembly_create_field_default(field_name)
        if field.type == "float":
            if default is None:
                return val is None or val is False
            try:
                return math.isclose(
                    float(val if val is not False and val is not None else 0.0),
                    float(default),
                    rel_tol=0.0,
                    abs_tol=1e-9,
                )
            except (TypeError, ValueError):
                return False
        if field.type == "integer":
            if default is None:
                return val is None or val is False
            try:
                return int(val) == int(default)
            except (TypeError, ValueError):
                return False
        if field.type == "boolean":
            return bool(val) == bool(default)
        if field.type in ("char", "text"):
            def_norm = "" if default in (None, False) else str(default)
            val_norm = "" if val in (None, False) else str(val)
            return val_norm == def_norm
        if field.type == "selection":
            return val == default
        if field.type == "many2one":
            def_id = default.id if default else False
            vid = val if isinstance(val, int) else (val[0] if val else False)
            return vid == def_id or (not vid and not def_id)
        return False

    @api.model
    def _create_vals_vote_type_ids_unspecified_or_empty(self, vals):
        if "vote_type_ids" not in vals:
            return True
        v = vals["vote_type_ids"]
        if not v:
            return True
        if isinstance(v, (list, tuple)) and len(v) == 1:
            cmd = v[0]
            if (
                isinstance(cmd, (list, tuple))
                and len(cmd) >= 3
                and cmd[0] == 6
                and not cmd[2]
            ):
                return True
        return False

    @api.model
    def _create_vals_partner_domain_unspecified_or_model_default(self, vals):
        if "partner_domain" not in vals:
            return True
        raw = vals.get("partner_domain")
        if raw in (None, False):
            return True
        val_s = str(raw).strip()
        def_raw = self._assembly_create_field_default("partner_domain")
        def_s = "[]" if def_raw in (None, False) else str(def_raw).strip()
        return val_s == def_s

    @api.model
    def _create_vals_char_address_unset(self, vals, field_name):
        if field_name not in vals:
            return True
        val = vals.get(field_name)
        if val in (None, False):
            return True
        return not str(val).strip()

    @api.model
    def _create_vals_many2one_unset(self, vals, field_name):
        if field_name not in vals:
            return True
        return not vals.get(field_name)

    @api.model
    def _apply_assembly_type_to_create_vals(self, vals, atype):
        """Copy template fields from ``assembly.type`` into create ``vals`` (AF §2.2).

        Fills gaps when keys are missing **or** still equal model defaults / empty,
        so browser creates (with ``default_*`` sent for every column) inherit quorum,
        ``vote_type_ids`` and ``partner_domain`` like :meth:`_onchange_assembly_type_id`.
        """
        if not atype.exists():
            return
        if self._create_vals_vote_type_ids_unspecified_or_empty(vals):
            vals["vote_type_ids"] = [(6, 0, atype.vote_type_ids.ids)]
        if self._create_vals_matches_assembly_field_default("quorum_type", vals):
            vals["quorum_type"] = atype.default_quorum_type
        if self._create_vals_matches_assembly_field_default("quorum_value", vals):
            vals["quorum_value"] = atype.default_quorum_value
        if self._create_vals_matches_assembly_field_default(
            "quorum_second_call_type", vals
        ):
            vals["quorum_second_call_type"] = atype.default_quorum_second_call_type
        if self._create_vals_matches_assembly_field_default(
            "quorum_second_call_value", vals
        ):
            vals["quorum_second_call_value"] = atype.default_quorum_second_call_value
        if self._create_vals_partner_domain_unspecified_or_model_default(vals):
            vals["partner_domain"] = atype.partner_domain or "[]"
        if self._create_vals_char_address_unset(vals, "street"):
            vals["street"] = atype.default_street
        if self._create_vals_char_address_unset(vals, "city"):
            vals["city"] = atype.default_city
        if self._create_vals_char_address_unset(vals, "zip"):
            vals["zip"] = atype.default_zip
        if self._create_vals_many2one_unset(vals, "state_id"):
            vals["state_id"] = (
                atype.default_state_id.id if atype.default_state_id else False
            )
        if self._create_vals_many2one_unset(vals, "country_id"):
            vals["country_id"] = (
                atype.default_country_id.id if atype.default_country_id else False
            )
        if self._create_vals_many2one_unset(vals, "president_id"):
            vals["president_id"] = (
                atype.default_president_id.id if atype.default_president_id else False
            )
        if self._create_vals_many2one_unset(vals, "secretary_id"):
            vals["secretary_id"] = (
                atype.default_secretary_id.id if atype.default_secretary_id else False
            )

    @api.model
    def _prepare_and_validate_assembly_create_vals_list(self, vals_list):
        for vals in vals_list:
            if vals.get("code", self.env._("New")) == self.env._("New"):
                vals["code"] = self.env["ir.sequence"].next_by_code(
                    "assembly.assembly"
                ) or self.env._("New")
            if vals.get("assembly_type_id"):
                atype = self.env["assembly.type"].browse(vals["assembly_type_id"])
                self._apply_assembly_type_to_create_vals(vals, atype)
            initial_state = vals.get("assembly_state", "draft")
            if initial_state != "draft":
                raise UserError(
                    self.env._(
                        "New assemblies must be created in draft status. "
                        "Got: %(state)s",
                        state=initial_state,
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        self._prepare_and_validate_assembly_create_vals_list(vals_list)
        return super().create(vals_list)

    @api.model
    def _assembly_is_allowed_state_transition(self, old_state, new_state):
        """Return whether ``old_state → new_state`` is structurally allowed.

        Same-state is handled by callers as a no-op. Rules:

        * Sequential: draft→announced→open→in_session→closed
        * From **any** lifecycle state (including closed): → cancelled
        * cancelled → draft (reopen)
        """
        return (old_state, new_state) in _ASSEMBLY_ALLOWED_STATE_TRANSITIONS

    def _validate_state_transition(self, old_state, new_state):
        if old_state == new_state:
            return
        if (
            new_state not in _ASSEMBLY_STATE_KEYS
            or old_state not in _ASSEMBLY_STATE_KEYS
        ):
            raise UserError(
                self.env._(
                    "Invalid assembly status transition: %(old)s → %(new)s",
                    old=old_state,
                    new=new_state,
                )
            )
        if not self.env["assembly.assembly"]._assembly_is_allowed_state_transition(
            old_state, new_state
        ):
            raise UserError(
                self.env._(
                    "Invalid assembly status transition: %(old)s → %(new)s",
                    old=old_state,
                    new=new_state,
                )
            )

    def _search_open_votings(self):
        self.ensure_one()
        return self.env["assembly.voting"].search(
            [
                ("agenda_id.assembly_id", "=", self.id),
                ("voting_state", "=", "open"),
            ]
        )

    def _search_all_votings(self):
        self.ensure_one()
        return self.env["assembly.voting"].search(
            [("agenda_id.assembly_id", "=", self.id)]
        )

    def _check_transition_prerequisites(self, old_state, new_state):
        self.ensure_one()
        if old_state == new_state:
            return
        if (old_state, new_state) == ("draft", "announced"):
            if not self.agenda_ids:
                raise UserError(
                    self.env._(
                        "At least one agenda item must be added before "
                        "the assembly can be announced."
                    )
                )
        if (old_state, new_state) == ("in_session", "closed"):
            if self._search_open_votings():
                raise UserError(
                    self.env._(
                        "Close or cancel all open votings before closing the assembly."
                    )
                )
            not_done = self.agenda_ids.filtered(
                lambda a: a.agenda_state not in ("voted", "skipped")
            )
            if not_done:
                raise UserError(
                    self.env._(
                        "All agenda items must be voted on or skipped "
                        "before closing the assembly."
                    )
                )

    def _prepare_state_transition_before_write(self, old_state, new_state):
        self.ensure_one()
        if old_state == new_state:
            return
        if new_state == "cancelled" and old_state != "cancelled":
            self._search_open_votings().with_context(
                **{CTX_ASSEMBLY_INTERNAL_TRANSITION: True}
            ).write({"voting_state": "cancelled"})
        if (old_state, new_state) == ("cancelled", "draft"):
            self.attendee_ids.unlink()
            self._search_all_votings().unlink()
            self.agenda_ids.write({"agenda_state": "pending"})

    def _validate_assembly_state_write_and_apply_transition_side_effects(self, vals):
        if "assembly_state" not in vals:
            return
        new_state = vals["assembly_state"]
        old_states_by_id = {rec.id: rec.assembly_state for rec in self}
        for rec in self:
            rec._validate_state_transition(old_states_by_id[rec.id], new_state)
        for rec in self:
            old_state = old_states_by_id[rec.id]
            if old_state == new_state:
                continue
            rec._check_transition_prerequisites(old_state, new_state)
            rec._prepare_state_transition_before_write(old_state, new_state)

    def _transition_assembly_state_via_write(self, new_state, extra_vals=None):
        self.ensure_one()
        vals = dict(extra_vals or ())
        vals["assembly_state"] = new_state
        return self.write(vals)

    def _transition_assembly_state(self, new_state, extra_vals=None):
        """Used by public lifecycle actions; same as :meth:`_transition_assembly_state_via_write`."""
        return self._transition_assembly_state_via_write(new_state, extra_vals)

    def _assembly_closed_write_allowed_vals(self, vals):
        """When ``assembly_state`` is ``closed``, only transition to ``cancelled`` is allowed."""
        if not vals:
            return True
        if (
            set(vals.keys()) == {"assembly_state"}
            and vals.get("assembly_state") == "cancelled"
        ):
            return True
        return False

    def _assembly_ensure_not_closed_for_related_changes(self):
        """Raise if any assembly in ``self`` is closed (child models call this).

        Skipped during :data:`CTX_ASSEMBLY_INTERNAL_TRANSITION` (e.g. cancel cascades).
        """
        if self.env.context.get(CTX_ASSEMBLY_INTERNAL_TRANSITION):
            return
        bad = self.filtered(lambda a: a.assembly_state == "closed")
        if bad:
            raise UserError(
                self.env._(
                    "This assembly is closed. You cannot change related records. "
                    "Use Cancel on the assembly if you need to void it."
                )
            )

    def write(self, vals):
        vals = dict(vals)
        self._validate_assembly_state_write_and_apply_transition_side_effects(vals)
        locked = self.filtered(lambda r: r.assembly_state == "closed")
        if locked and not locked._assembly_closed_write_allowed_vals(vals):
            raise UserError(
                self.env._(
                    "This assembly is closed and cannot be edited. "
                    "Use Cancel if you need to void it (then you may reopen from cancelled)."
                )
            )
        res = super().write(vals)
        if "vote_type_ids" in vals:
            attendees = self.mapped("attendee_ids")
            if attendees:
                self.env["assembly.attendee"].recompute_votes(attendees)
        return res

    def _get_active_quorum_rule(self):
        self.ensure_one()
        if self.is_second_call:
            return self.quorum_second_call_type, self.quorum_second_call_value
        return self.quorum_type, self.quorum_value

    def _get_possible_attendees_count(self):
        self.ensure_one()
        return self.env["res.partner"].search_count(self._get_partner_domain())

    # --- Quorum presence (people only): implementation of _get_present_partner_ids ---

    def _present_quorum_convocable_partner_ids(self):
        """Partners in the assembly convocation domain (same pool as *possible* count)."""
        self.ensure_one()
        return frozenset(self.env["res.partner"].search(self._get_partner_domain()).ids)

    def _present_quorum_confirmed_attendee_partner_ids(self):
        """Partners with ``attendee_state == confirmed`` on this assembly."""
        self.ensure_one()
        confirmed = self.attendee_ids.filtered_domain(
            [("attendee_state", "=", "confirmed")]
        )
        return frozenset(pid for pid in confirmed.mapped("partner_id").ids if pid)

    def _present_quorum_represented_delegator_partner_ids(
        self, confirmed_partner_ids, convocable_partner_ids
    ):
        """Delegators counted only via representation (excludes already-confirmed attendees).

        Each id is ``delegation.partner_id`` for a confirmed delegation that passes
        quorum partner rules (delegate is confirmed attendee here). Partial
        ``vote_type_ids`` still counts — presence is per person, not per vote unit.
        """
        self.ensure_one()
        confirmed = frozenset(confirmed_partner_ids)
        convocable = frozenset(convocable_partner_ids)
        extra = set()
        Delegation = self.env["assembly.delegation"]
        for delegation in Delegation._get_effective_delegations(
            delegations=self.delegation_ids
        ):
            pid = delegation.partner_id.id
            if not pid or pid not in convocable or pid in confirmed:
                continue
            extra.add(pid)
        return frozenset(extra)

    def _get_present_partner_ids(self):
        """Distinct ``res.partner`` ids counted for quorum presence (people only).

        **Single entry point** for “who is present” for quorum: every stored quorum
        field and check must derive counts from this set (or its length), not from
        vote lines or ``partner.vote`` magnitudes.

        **A — Confirmed attendees:** ``partner_id`` of rows with
        ``attendee_state == confirmed``.

        **B — Represented delegators (no attendee row required):** partners in the
        convocation domain who are *not* in A and appear as ``delegation.partner_id``
        on at least one confirmed, quorum-effective delegation (delegate is a
        confirmed attendee); partial ``vote_type_ids`` on the delegation still counts
        one person.

        Returns ``frozenset(A | B)`` (set union ⇒ each partner at most once).
        Cancelled assemblies → empty frozenset.

        Does not read ``partner.vote`` nor ``assembly.attendee.vote`` totals.
        """
        self.ensure_one()
        if self.assembly_state == "cancelled":
            return frozenset()
        confirmed = self._present_quorum_confirmed_attendee_partner_ids()
        convocable = self._present_quorum_convocable_partner_ids()
        represented = self._present_quorum_represented_delegator_partner_ids(
            confirmed, convocable
        )
        return frozenset(confirmed | represented)

    def _get_quorum_present_people_count(self):
        """Headcount of distinct partners considered present for quorum.

        Equivalent to ``len(self._get_present_partner_ids())``; use when you need only
        the scalar (e.g. performance tests). Stored ``total_present_attendees`` uses
        the same length in :meth:`_compute_quorum`.
        """
        self.ensure_one()
        return len(self._get_present_partner_ids())

    def _count_present_attendees(self):
        """Same as :meth:`_get_quorum_present_people_count` (explicit name for call sites)."""
        return self._get_quorum_present_people_count()

    def _is_quorum_reached(self, present_partner_ids, possible, quorum_percentage=None):
        """Whether the active quorum rule passes.

        ``present_partner_ids`` must be the same frozenset as
        :meth:`_get_present_partner_ids` for this record (callers pass it to avoid a
        second recomputation of the set in :meth:`_compute_quorum`).
        """
        self.ensure_one()
        if possible <= 0:
            return False
        present = len(present_partner_ids)
        pct = (
            quorum_percentage
            if quorum_percentage is not None
            else _quorum_present_percentage(present, possible)
        )
        qtype, qval = self._get_active_quorum_rule()
        if qtype == "any":
            return present > 0
        if qtype == "percentage":
            return pct >= qval
        return present >= qval

    def _session_start_ui_result(self, write_result):
        self.ensure_one()
        if self.quorum_reached:
            return write_result
        return {
            "warning": {
                "title": self.env._("Quorum not reached"),
                "message": self.env._(
                    "Quorum has not been reached. You may still start the session."
                ),
            },
        }

    def _action_open_related(self, res_model, title):
        self.ensure_one()
        return self._action_window(
            res_model,
            title,
            "list,form",
            domain=[("assembly_id", "=", self.id)],
            context={"default_assembly_id": self.id},
        )

    def action_announce(self):
        return self._transition_assembly_state("announced")

    def action_open_registration(self):
        return self._transition_assembly_state("open")

    def action_start_session(self):
        res = self._transition_assembly_state(
            "in_session", {"date_start": fields.Datetime.now()}
        )
        return self._session_start_ui_result(res)

    def action_close(self):
        return self._transition_assembly_state(
            "closed", {"date_end": fields.Datetime.now()}
        )

    def action_cancel(self):
        return self._transition_assembly_state("cancelled")

    def action_reopen(self):
        return self._transition_assembly_state("draft")

    def action_generate_attendees(self):
        self.ensure_one()
        if self.assembly_state not in _ASSEMBLY_STATES_ALLOW_GENERATE_ATTENDEES:
            raise UserError(self.env._("Cannot generate attendees in current state."))
        domain = expression.AND(
            [self._get_partner_domain(), [("assembly_excluded", "=", False)]]
        )
        partners = self.env["res.partner"].search(domain)
        existing = self.attendee_ids.mapped("partner_id")
        to_create = partners - existing
        if to_create:
            self.env["assembly.attendee"].create(
                [
                    {"assembly_id": self.id, "partner_id": partner.id}
                    for partner in to_create
                ]
            )
        if self.attendee_ids:
            self.env["assembly.attendee"].recompute_votes(self.attendee_ids)

    def action_recompute_attendee_votes(self):
        """AF §6: Recompute stored vote lines for all attendees from base_vote and delegations."""
        self.ensure_one()
        if not self.attendee_ids:
            return True
        self.env["assembly.attendee"].recompute_votes(self.attendee_ids)
        return True

    def get_rendered_publication_text(self):
        return ""

    def get_rendered_delegation_document_text(self):
        return ""

    def get_rendered_delegation_footer_text(self):
        return ""

    def get_rendered_ballot_intro_text(self):
        return ""

    def get_rendered_ballot_nominative_intro_text(self):
        return ""

    def action_open_agenda_items(self):
        self.ensure_one()
        return self._action_window(
            "assembly.agenda",
            self.env._("Agenda items"),
            "list,kanban,graph,pivot,form",
            domain=[("assembly_id", "=", self.id)],
            context={"default_assembly_id": self.id},
        )

    def action_open_votings(self):
        """Open all votings for this assembly (list + form)."""
        self.ensure_one()
        return self._action_window(
            "assembly.voting",
            self.env._("Votings"),
            "list,kanban,graph,pivot,form",
            domain=[("assembly_id", "=", self.id)],
        )

    def action_open_delegations(self):
        return self._action_open_related(
            "assembly.delegation", self.env._("Delegations")
        )

    def action_open_attendees(self):
        return self._action_open_related("assembly.attendee", self.env._("Attendees"))
