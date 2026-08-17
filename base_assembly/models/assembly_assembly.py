# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
# pylint: disable=too-many-lines

import math
from datetime import datetime, time, timedelta

import pytz
from markupsafe import Markup
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import format_datetime, is_html_empty
from odoo.tools.misc import clean_context
from odoo.tools.safe_eval import safe_eval

from .assembly_mixin import assembly_safe_report_filename

_DOMAIN_OPERATORS = frozenset(("&", "|", "!"))

_ASSEMBLY_STATE_KEYS = frozenset(
    {"draft", "announced", "in_session", "closed", "cancelled"}
)

# Forward lifecycle (one step at a time).
_ASSEMBLY_SEQUENTIAL_TRANSITIONS = frozenset(
    {
        ("draft", "announced"),
        ("announced", "in_session"),
        ("in_session", "closed"),
    }
)

# Full allow-list: sequential edges + cancel from any state + reopen from cancelled.
_ASSEMBLY_ALLOWED_STATE_TRANSITIONS = frozenset(
    set(_ASSEMBLY_SEQUENTIAL_TRANSITIONS)
    | {(s, "cancelled") for s in _ASSEMBLY_STATE_KEYS}
    | {("cancelled", "draft")}
)

_ASSEMBLY_STATES_ALLOW_GENERATE_ATTENDEES = frozenset(("draft",))

# Set on ``assembly.assembly`` writes that cascade to related models while the
# assembly row still reads ``closed`` (e.g. cancel → close open votings).
CTX_ASSEMBLY_INTERNAL_TRANSITION = "assembly_internal_transition"

# Set only by :meth:`AssemblyAssembly.action_reopen_from_closed` so the
# ``closed → in_session`` edge is not writable from RPC without audit
# (chatter) and ACL.
CTX_ASSEMBLY_REOPEN_FROM_CLOSED = "assembly_reopen_from_closed"


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


# Maps assembly document text field -> assembly.type default field (copied on create).
_TYPE_TEXT_DEFAULTS = {
    "description": "default_publication_text",
    "delegation_document_text": "default_delegation_document_text",
    "delegation_footer_text": "default_delegation_footer_text",
    "representation_document_text": "default_representation_document_text",
    "ballot_intro_text": "default_ballot_intro_text",
    "ballot_nominative_intro_text": "default_ballot_nominative_intro_text",
    "final_text": "default_final_text",
}


class AssemblyAssembly(models.Model):  # pylint: disable=too-many-public-methods
    """Assembly lifecycle and convocation.

    **Attendance “present people” (single source):** distinct ``res.partner`` ids
    for the assembly come only from :meth:`_get_present_partner_ids` (confirmed
    attendees plus represented delegators in the convocation domain). Stored
    ``total_present_attendees`` in :meth:`_compute_attendee_counts` is derived solely
    from that set; ``total_possible_attendees`` from the convocation pool size (same
    domain as :meth:`_get_possible_attendees_count`).
    """

    _name = "assembly.assembly"
    _inherit = ["mail.thread"]
    _description = "Assembly"
    _order = "date_first_call desc, id desc"

    _sql_constraints = [
        (
            "assembly_company_code_uniq",
            "UNIQUE(company_id, code)",
            "The assembly reference code must be unique per company.",
        ),
        (
            "assembly_name_company_uniq",
            "UNIQUE(company_id, name)",
            "An assembly with this name already exists in this company.",
        ),
    ]

    def _get_report_base_filename(self):
        self.ensure_one()
        return assembly_safe_report_filename(
            self.display_name, default=self.env._("Assembly")
        )

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
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
        check_company=True,
    )
    date_announcement = fields.Date(
        string="Notice date",
        default=fields.Date.context_today,
    )
    date_first_call = fields.Datetime(string="First call", index=True)
    date_second_call = fields.Datetime(string="Second call")
    date_start = fields.Date(string="Assembly date")
    date_end = fields.Datetime(string="Session end")
    location = fields.Char(
        help="Short venue label (e.g. room or building) for headers; use address "
        "fields for postal details in documents.",
    )
    street = fields.Char()
    city = fields.Char(
        string="City (manual)",
        help="Free text for documents when not using the city directory.",
    )
    city_id = fields.Many2one(
        "res.city",
        string="City (directory)",
        ondelete="set null",
        domain="[('country_id', '=?', country_id), ('state_id', '=?', state_id)]",
    )
    zip = fields.Char(string="ZIP")
    state_id = fields.Many2one(
        "res.country.state", string="State/Province", ondelete="restrict"
    )
    country_id = fields.Many2one("res.country", ondelete="restrict")
    president_id = fields.Many2one(
        "res.users",
        ondelete="set null",
    )
    secretary_id = fields.Many2one(
        "res.users",
        ondelete="set null",
    )
    description = fields.Html(string="Convocation text", sanitize=False, translate=True)
    delegation_document_text = fields.Html(
        string="Delegation document text",
        sanitize=False,
        translate=True,
        help="Delegation PDF introduction. Supports placeholders like "
        "{{ object.name }}.",
    )
    delegation_footer_text = fields.Html(
        string="Delegation footer text",
        sanitize=False,
        translate=True,
    )
    representation_document_text = fields.Html(
        string="Representation document text",
        sanitize=False,
        translate=True,
        help="Representation PDF introduction. Supports placeholders like "
        "{{ object.name }}.",
    )
    notes = fields.Html(sanitize=False)
    internal_notes = fields.Html(string="Internal notes", sanitize=False)
    ballot_intro_text = fields.Html(
        string="Ballot introduction text",
        sanitize=False,
        translate=True,
    )
    ballot_nominative_intro_text = fields.Html(
        string="Nominative ballot introduction text",
        sanitize=False,
        translate=True,
    )
    final_text = fields.Html(
        string="Final text",
        sanitize=False,
        translate=True,
        help="Closing paragraph printed after the agenda on the convocation.",
    )
    assembly_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("announced", "Announced"),
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
    allow_online_voting = fields.Boolean(
        string="Allow online voting",
        default=False,
        help=(
            "When enabled, eligible portal users may cast votes through the website "
            "for open votings of this assembly (subject to portal routes)."
        ),
    )
    attendance_require_partner_vat_confirm = fields.Boolean(
        string="Require TIN to mark attended",
        default=False,
        help=(
            "When set, recording a member as attended (confirmed present) is "
            "blocked if the member has no TIN (VAT) or it is the exempt "
            "placeholder (/)."
        ),
    )
    attendance_partner_vat_format_strict = fields.Boolean(
        string="Strict TIN format when marking attended",
        default=False,
        help=(
            "When set together with the requirement above, the TIN must pass a light "
            "normalized format check (alphanumeric characters, minimum length)."
        ),
    )
    allow_attendance_notes = fields.Boolean(
        string="Allow attendance annotations",
        default=True,
        help=(
            "If disabled, attendance notes are hidden and cannot be set on "
            "registrations."
        ),
    )
    include_qr_code = fields.Boolean(
        string="Tracked attendance links & QR",
        default=lambda self: bool(self.env.company.assembly_default_use_qr),
        help=(
            "When enabled, each attendee gets a short link-tracker URL to the "
            "attendance flow (opens counted) and the same URL can be shown as a QR "
            "code. Managers open it from the assembly smart button Links & QR, from "
            "each attendee form (header: Open attendance link / Show QR), or from the "
            "Configuration tab help on this assembly. When disabled, existing trackers "
            "for this assembly's attendees are cleared and new ones are not created. "
            "Landing and error pages: Settings → Assemblies → Attendance deep links."
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
    representation_ids = fields.One2many(
        "assembly.representation",
        "assembly_id",
        string="Representations",
    )
    total_possible_attendees = fields.Integer(
        string="Possible attendees",
        compute="_compute_attendee_counts",
        store=True,
    )
    total_present_attendees = fields.Integer(
        string="Present attendees",
        compute="_compute_attendee_counts",
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
    count_representations = fields.Integer(
        string="Representations count",
        compute="_compute_counts",
    )
    voting_sessions_count = fields.Integer(
        string="Voting sessions",
        compute="_compute_counts",
        help="Number of assembly.voting records linked to this assembly's agenda.",
    )
    mail_outbound_email_count = fields.Integer(
        string="Outgoing emails",
        compute="_compute_mail_trace_counters",
    )
    attendee_tracked_link_count = fields.Integer(
        string="Attendance links ready",
        compute="_compute_attendee_tracked_link_count",
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
    kanban_call_day = fields.Char(
        string="Kanban first call day",
        compute="_compute_kanban_call_datetime_parts",
    )
    kanban_call_month_year = fields.Char(
        string="Kanban first call month year",
        compute="_compute_kanban_call_datetime_parts",
    )
    kanban_call_time = fields.Char(
        string="Kanban first call time",
        compute="_compute_kanban_call_datetime_parts",
    )
    kanban_location_label = fields.Char(
        string="Kanban location label",
        compute="_compute_kanban_location_label",
    )

    @api.depends("date_first_call")
    def _compute_kanban_call_datetime_parts(self):
        for record in self:
            if not record.date_first_call:
                record.kanban_call_day = ""
                record.kanban_call_month_year = ""
                record.kanban_call_time = ""
                continue
            d = record.date_first_call
            env = record.env
            record.kanban_call_day = format_datetime(env, d, dt_format="d")
            month_year = format_datetime(env, d, dt_format="MMM y")
            record.kanban_call_month_year = month_year.replace(" ", ". ").upper()
            record.kanban_call_time = format_datetime(env, d, dt_format="HH:mm")

    @api.depends("city", "city_id", "state_id")
    def _compute_kanban_location_label(self):
        for record in self:
            city_name = (record.city_id.name if record.city_id else record.city) or ""
            state_name = record.state_id.name if record.state_id else ""
            if city_name and state_name:
                record.kanban_location_label = "%s (%s)" % (city_name, state_name)
            elif city_name:
                record.kanban_location_label = city_name
            elif state_name:
                record.kanban_location_label = state_name
            else:
                record.kanban_location_label = ""

    @api.depends(
        "agenda_ids",
        "delegation_ids",
        "representation_ids",
        "agenda_ids.voting_ids",
    )
    def _compute_counts(self):
        for record in self:
            record.count_agenda_items = len(record.agenda_ids)
            record.count_delegations = len(record.delegation_ids)
            record.count_representations = len(record.representation_ids)
            record.voting_sessions_count = len(record.agenda_ids.mapped("voting_ids"))

    @api.depends("message_ids")
    def _compute_mail_trace_counters(self):
        mail_mail = self.env["mail.mail"]
        for record in self:
            record.mail_outbound_email_count = mail_mail.search_count(
                [
                    ("model", "=", "assembly.assembly"),
                    ("res_id", "=", record.id),
                ]
            )

    @api.depends(
        "include_qr_code",
        "attendee_ids",
        "attendee_ids.attendance_link_tracker_id",
    )
    def _compute_attendee_tracked_link_count(self):
        for record in self:
            if not record.include_qr_code:
                record.attendee_tracked_link_count = 0
            else:
                record.attendee_tracked_link_count = len(
                    record.attendee_ids.filtered("attendance_link_tracker_id")
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
        for record in self:
            votings = record.agenda_ids.mapped("voting_ids")
            record.kanban_open_votings_count = len(
                votings.filtered(lambda v: v.voting_state == "open")
            )
            closed_v = votings.filtered(lambda v: v.voting_state == "closed")
            record.kanban_closed_votings_count = len(closed_v)
            if closed_v:
                record.kanban_avg_participation = sum(
                    closed_v.mapped("participation_percentage")
                ) / len(closed_v)
            else:
                record.kanban_avg_participation = 0.0
            summary = ""
            voting_result = self.env["assembly.voting.result"]
            opt_labels = dict(
                voting_result._fields["vote_option"]._description_selection(self.env)
            )
            # ``date_close`` can be False; sorting by field name mixes bool
            # with datetime.
            epoch_close = fields.Datetime.from_string("1970-01-01 00:00:00")
            for voting in closed_v.sorted(
                key=lambda v, ep=epoch_close: v.date_close or ep,
                reverse=True,
            ):
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
            record.kanban_results_summary = summary

    @api.depends(
        "partner_domain",
        "assembly_state",
        "attendee_ids",
        "attendee_ids.attendee_state",
        "attendee_ids.partner_id",
        "delegation_ids",
        "delegation_ids.partner_id",
        "delegation_ids.delegate_partner_id",
        "delegation_ids.vote_type_ids",
    )
    def _compute_attendee_counts(self):
        if self.ids:
            self.fetch(
                ["attendee_ids", "delegation_ids", "partner_domain", "assembly_state"]
            )
        # DISTINCT people in the convocation who are confirmed and/or represented by
        # an effective vote delegation. Does not depend on ``partner.vote``,
        # ``assembly.attendee.vote``, vote types, or any vote totals (@api.depends
        # above must stay free of those models).
        for record in self:
            if record.assembly_state == "cancelled":
                possible = record._get_possible_attendees_count()
                present_partner_ids = frozenset()
            else:
                convocable = record._present_quorum_convocable_partner_ids()
                possible = len(convocable)
                present_partner_ids = record._get_present_partner_ids(
                    convocable_partner_ids=convocable
                )
            record.total_possible_attendees = possible
            record.total_present_attendees = len(present_partner_ids)

    def _assembly_date_coherence_issue_messages(self):
        self.ensure_one()
        msgs = []
        if self.date_first_call and self.date_second_call:
            if self.date_second_call <= self.date_first_call:
                msgs.append(
                    self.env._("Second call must be strictly after the first call.")
                )
        if self.date_announcement and self.date_start:
            if self.date_announcement > self.date_start:
                msgs.append(
                    self.env._("Notice date cannot be after the assembly date.")
                )
        if self.date_start and self.date_end:
            if fields.Date.to_date(self.date_end) < self.date_start:
                msgs.append(
                    self.env._("Session end cannot be before the assembly date.")
                )
        return msgs

    @api.constrains(
        "date_announcement",
        "date_first_call",
        "date_second_call",
        "date_start",
        "date_end",
    )
    def _check_assembly_date_coherence(self):
        for record in self:
            msgs = record._assembly_date_coherence_issue_messages()
            if msgs:
                raise ValidationError("\n".join(msgs))

    @api.onchange(
        "date_announcement",
        "date_first_call",
        "date_second_call",
        "date_start",
        "date_end",
    )
    def _onchange_assembly_date_coherence_warn(self):
        if not self:
            return None
        msgs = self._assembly_date_coherence_issue_messages()
        if not msgs:
            return None
        return {
            "warning": {
                "title": self.env._("Invalid dates"),
                "message": "\n".join(msgs),
            }
        }

    @api.onchange("date_start")
    def _onchange_date_start_sync_calls(self):
        """Set first call at 00:00 and second call 30 min later (user adjusts)."""
        if not self.date_start:
            return
        tz = pytz.timezone(self.env.context.get("tz") or self.env.user.tz or "UTC")
        local_midnight = tz.localize(datetime.combine(self.date_start, time.min))
        utc_dt = local_midnight.astimezone(pytz.utc).replace(tzinfo=None)
        self.date_first_call = utc_dt
        self.date_second_call = utc_dt + timedelta(minutes=30)

    @api.onchange("assembly_type_id")
    def _onchange_assembly_type_id(self):
        if self.assembly_type_id:
            t = self.assembly_type_id
            if t.company_id:
                self.company_id = t.company_id
            self.vote_type_ids = t.vote_type_ids
            self.partner_domain = t.partner_domain or "[]"
            self.street = t.default_street
            if t.default_city_id:
                self.city_id = t.default_city_id
                self.city = t.default_city_id.name
                if t.default_city_id.zipcode:
                    self.zip = t.default_city_id.zipcode
                self.state_id = t.default_city_id.state_id
                self.country_id = t.default_city_id.country_id
            else:
                self.city_id = False
                self.city = t.default_city
                self.zip = t.default_zip
                self.state_id = t.default_state_id
                self.country_id = t.default_country_id
            self.president_id = t.default_president_id
            self.secretary_id = t.default_secretary_id
            self.attendance_require_partner_vat_confirm = (
                t.default_attendance_require_partner_vat_confirm
            )
            self.attendance_partner_vat_format_strict = (
                t.default_attendance_partner_vat_format_strict
            )
            self.allow_attendance_notes = t.default_allow_attendance_notes
            self.include_qr_code = t.default_include_qr_code

    @api.onchange("country_id")
    def _onchange_assembly_country_id(self):
        if (
            self.state_id
            and self.country_id
            and self.state_id.country_id != self.country_id
        ):
            self.state_id = False
        if (
            self.city_id
            and self.country_id
            and self.city_id.country_id != self.country_id
        ):
            self.city_id = False

    @api.onchange("state_id")
    def _onchange_assembly_state_id(self):
        if self.state_id:
            self.country_id = self.state_id.country_id

    @api.onchange("city_id")
    def _onchange_assembly_city_id(self):
        if self.city_id:
            self.city = self.city_id.name
            if self.city_id.zipcode:
                self.zip = self.city_id.zipcode
            self.state_id = self.city_id.state_id
            self.country_id = self.city_id.country_id

    @api.onchange("city")
    def _onchange_assembly_city_char(self):
        if (
            self.city_id
            and (self.city or "").strip() != (self.city_id.name or "").strip()
        ):
            self.city_id = False

    def _get_partner_domain(self):
        self.ensure_one()
        return _eval_partner_domain_text(self.partner_domain)

    @api.model
    def _assembly_create_field_default(self, field_name):
        """Default value for ``field_name`` on a new assembly."""
        field = self._fields[field_name]
        default = field.default
        if default is None:
            return None
        if callable(default):
            return default(self)
        return default

    @api.model
    def _create_vals_matches_assembly_field_default(self, field_name, vals):
        # pylint: disable=too-many-return-statements
        """Whether ``vals[field_name]`` is absent or still the model field default.

        Web create often sends all columns with model defaults; then
        :meth:`_apply_assembly_type_to_create_vals` must still copy the type.
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
        """Copy template fields from ``assembly.type`` into create ``vals``.

        Fills gaps when keys are missing **or** still equal model defaults /
        empty, so browser creates (with ``default_*`` sent for every column)
        inherit quorum, ``vote_type_ids`` and ``partner_domain`` like
        :meth:`_onchange_assembly_type_id`.
        """
        if not atype.exists():
            return
        if self._create_vals_vote_type_ids_unspecified_or_empty(vals):
            vals["vote_type_ids"] = [(6, 0, atype.vote_type_ids.ids)]
        if self._create_vals_partner_domain_unspecified_or_model_default(vals):
            vals["partner_domain"] = atype.partner_domain or "[]"
        self._apply_type_address_defaults(vals, atype)
        self._apply_type_attendance_defaults(vals, atype)
        if atype.company_id and self._create_vals_company_matches_default_or_empty(
            vals
        ):
            vals["company_id"] = atype.company_id.id

    @api.model
    def _apply_type_address_defaults(self, vals, atype):
        """Copy address/officer defaults from the assembly type when unset."""
        if self._create_vals_char_address_unset(vals, "street"):
            vals["street"] = atype.default_street
        if self._create_vals_many2one_unset(vals, "city_id") and atype.default_city_id:
            vals["city_id"] = atype.default_city_id.id
            self._assembly_apply_city_id_to_vals(vals)
        elif self._create_vals_char_address_unset(vals, "city"):
            vals["city"] = atype.default_city
            vals["city_id"] = False
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
    def _apply_type_attendance_defaults(self, vals, atype):
        """Copy attendance/TIN defaults from the assembly type when at default."""
        if self._create_vals_matches_assembly_field_default(
            "attendance_require_partner_vat_confirm", vals
        ):
            vals["attendance_require_partner_vat_confirm"] = (
                atype.default_attendance_require_partner_vat_confirm
            )
        if self._create_vals_matches_assembly_field_default(
            "attendance_partner_vat_format_strict", vals
        ):
            vals["attendance_partner_vat_format_strict"] = (
                atype.default_attendance_partner_vat_format_strict
            )
        if self._create_vals_matches_assembly_field_default(
            "allow_attendance_notes", vals
        ):
            vals["allow_attendance_notes"] = atype.default_allow_attendance_notes
        if self._create_vals_matches_assembly_field_default("include_qr_code", vals):
            vals["include_qr_code"] = atype.default_include_qr_code

    @api.model
    def _create_vals_company_matches_default_or_empty(self, vals):
        """True if ``company_id`` is unset or still the model default (web create)."""
        if "company_id" not in vals or not vals.get("company_id"):
            return True
        default_c = self._assembly_create_field_default("company_id")
        if not default_c:
            return False
        return vals.get("company_id") in (default_c.id, default_c)

    @api.model
    def _prepare_and_validate_assembly_create_vals_list(self, vals_list):
        for vals in vals_list:
            if vals.get("code", self.env._("New")) == self.env._("New"):
                cid = vals.get("company_id") or self.env.company.id
                company = self.env["res.company"].browse(cid)
                seq = company.assembly_sequence_id
                if seq:
                    next_code = seq.next_by_id()
                else:
                    next_code = (
                        self.env["ir.sequence"]
                        .with_company(cid)
                        .next_by_code("assembly.assembly")
                    )
                vals["code"] = next_code or self.env._("New")
            if vals.get("assembly_type_id"):
                atype = self.env["assembly.type"].browse(vals["assembly_type_id"])
                self._apply_assembly_type_to_create_vals(vals, atype)
            else:
                cid = vals.get("company_id") or self.env.company.id
                company = self.env["res.company"].browse(cid)
                if self._create_vals_matches_assembly_field_default(
                    "include_qr_code", vals
                ):
                    vals["include_qr_code"] = bool(company.assembly_default_use_qr)
            initial_state = vals.get("assembly_state", "draft")
            if initial_state != "draft":
                raise UserError(
                    self.env._(
                        "New assemblies must be created in draft status. "
                        "Got: %(state)s",
                        state=initial_state,
                    )
                )
            self._assembly_apply_city_id_to_vals(vals)

    @api.model
    def _assembly_apply_city_id_to_vals(self, vals):
        cid = vals.get("city_id")
        if not cid:
            return
        city = self.env["res.city"].browse(cid)
        if not city.exists():
            return
        vals.setdefault("city", city.name)
        if city.zipcode:
            vals.setdefault("zip", city.zipcode)
        if city.state_id:
            vals.setdefault("state_id", city.state_id.id)
        if city.country_id:
            vals.setdefault("country_id", city.country_id.id)

    @api.model_create_multi
    def create(self, vals_list):
        provided_texts = [
            {f for f in _TYPE_TEXT_DEFAULTS if not is_html_empty(v.get(f))}
            for v in vals_list
        ]
        self._prepare_and_validate_assembly_create_vals_list(vals_list)
        assemblies = super().create(vals_list)
        for assembly, provided in zip(assemblies, provided_texts):
            assembly._copy_type_document_text_translations(provided)
        return assemblies

    def _copy_type_document_text_translations(self, provided_fields):
        """Copy the assembly type document texts, keeping all translations.

        Members may use different languages, so every installed-language value
        from the type is copied to the assembly; documents rendered later for
        each recipient then come out in that recipient's language. Fields the
        user already filled in are left untouched.
        """
        self.ensure_one()
        atype = self.assembly_type_id
        if not atype:
            return
        # en_US is the source language and may be absent from get_installed().
        langs = {code for code, __ in self.env["res.lang"].get_installed()} | {"en_US"}
        for asm_field, type_field in _TYPE_TEXT_DEFAULTS.items():
            if asm_field in provided_fields:
                continue
            translations = {}
            for lang in langs:
                value = atype.with_context(lang=lang)[type_field]
                if value:
                    translations[lang] = value
            if translations:
                self.update_field_translations(asm_field, translations)

    @api.model
    def _assembly_is_allowed_state_transition(self, old_state, new_state):
        """Return whether ``old_state → new_state`` is structurally allowed.

        Same-state is handled by callers as a no-op. Rules:

        * Sequential: draft→announced→open→in_session→closed
        * From **any** lifecycle state (including closed): → cancelled
        * cancelled → draft (reopen)
        * closed → in_session only with :data:`CTX_ASSEMBLY_REOPEN_FROM_CLOSED`
        """
        if (old_state, new_state) in _ASSEMBLY_ALLOWED_STATE_TRANSITIONS:
            return True
        if (old_state, new_state) == ("closed", "in_session"):
            return bool(self.env.context.get(CTX_ASSEMBLY_REOPEN_FROM_CLOSED))
        return False

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
                lambda a: a.agenda_state not in ("voted", "skipped", "addressed")
            )
            if not_done:
                raise UserError(
                    self.env._(
                        "All agenda items must be voted on, addressed or skipped "
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
        if (old_state, new_state) == ("draft", "announced"):
            self.action_generate_attendees()
        if (old_state, new_state) == ("cancelled", "draft"):
            self.attendee_ids.unlink()
            self._search_all_votings().unlink()
            self.agenda_ids.write({"agenda_state": "pending"})

    def _validate_assembly_state_write_and_apply_transition_side_effects(self, vals):
        if "assembly_state" not in vals:
            return
        new_state = vals["assembly_state"]
        old_states_by_id = {rec.id: rec.assembly_state for rec in self}
        for record in self:
            record._validate_state_transition(old_states_by_id[record.id], new_state)
        for record in self:
            old_state = old_states_by_id[record.id]
            if old_state == new_state:
                continue
            record._check_transition_prerequisites(old_state, new_state)
            record._prepare_state_transition_before_write(old_state, new_state)

    def _transition_assembly_state(self, new_state, extra_vals=None):
        self.ensure_one()
        vals = dict(extra_vals or ())
        vals["assembly_state"] = new_state
        return self.write(vals)

    def _assembly_closed_write_allowed_vals(self, vals):
        """When ``assembly_state`` is ``closed``, only controlled transitions apply."""
        if not vals:
            return True
        if set(vals.keys()) != {"assembly_state"}:
            return False
        new_state = vals.get("assembly_state")
        if new_state == "cancelled":
            return True
        if new_state == "in_session" and self.env.context.get(
            CTX_ASSEMBLY_REOPEN_FROM_CLOSED
        ):
            return True
        return False

    @api.model
    def _assembly_raise_if_closed(self, assemblies):
        if self.env.context.get(CTX_ASSEMBLY_INTERNAL_TRANSITION):
            return
        bad = assemblies.filtered(
            lambda a: a.assembly_state == "closed"
            and not a.company_id.assembly_allow_edit_closed_assembly
        )
        if bad:
            raise UserError(
                self.env._("This assembly is closed and cannot be modified.")
            )

    def _assembly_ensure_not_closed_for_related_changes(self):
        self.env["assembly.assembly"]._assembly_raise_if_closed(self)

    def unlink(self):
        for record in self:
            if (
                record.assembly_state == "closed"
                and not record.company_id.assembly_allow_edit_closed_assembly
            ):
                raise UserError(  # pylint: disable=no-raise-unlink
                    self.env._("This assembly is closed and cannot be modified.")
                )
        return super().unlink()

    def write(self, vals):
        vals = dict(vals)
        self._assembly_apply_city_id_to_vals(vals)
        self._validate_assembly_state_write_and_apply_transition_side_effects(vals)
        locked = self.filtered(
            lambda r: r.assembly_state == "closed"
            and not r.company_id.assembly_allow_edit_closed_assembly
        )
        if locked and not locked._assembly_closed_write_allowed_vals(vals):
            raise UserError(
                self.env._("This assembly is closed and cannot be modified.")
            )
        res = super().write(vals)
        if "vote_type_ids" in vals:
            attendees = self.mapped("attendee_ids")
            if attendees:
                self.env["assembly.attendee"].recompute_votes(attendees)
        if "include_qr_code" in vals:
            for record in self:
                if record.attendee_ids:
                    record.attendee_ids._sync_attendance_link_trackers()
        return res

    def _get_possible_attendees_count(self):
        self.ensure_one()
        return self.env["res.partner"].search_count(self._get_partner_domain())

    # --- Quorum presence (people only): implementation of _get_present_partner_ids ---

    def _present_quorum_convocable_partner_ids(self):
        """Partners in the convocation domain (same pool as *possible* count)."""
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
        """Delegators counted via **vote delegation** (not ``assembly.representation``).

        Excludes partners who already have a confirmed attendee row, and delegators
        with an ``absent`` attendee row (aligned with inbound vote snapshots, which
        ignore absent delegators). Each remaining id is ``delegation.partner_id``
        for a confirmed delegation that passes quorum partner rules (delegate is a
        confirmed attendee here). Partial ``vote_type_ids`` still counts one person.
        """
        self.ensure_one()
        confirmed = frozenset(confirmed_partner_ids)
        convocable = frozenset(convocable_partner_ids)
        extra = set()
        delegation_model = self.env["assembly.delegation"]
        delegations_eff = delegation_model._get_effective_delegations(
            delegations=self.delegation_ids
        )
        delegator_pids = {d.partner_id.id for d in delegations_eff if d.partner_id}
        absent_delegator_pids = frozenset()
        if delegator_pids:
            attendee_model = self.env["assembly.attendee"]
            att_lines = attendee_model._search_attendees_for_assembly(
                self.id, partner_ids=list(delegator_pids)
            )
            absent_delegator_pids = frozenset(
                att_lines.filtered_domain([("attendee_state", "=", "absent")])
                .mapped("partner_id")
                .ids
            )
        for delegation in delegations_eff:
            pid = delegation.partner_id.id
            if (
                not pid
                or pid not in convocable
                or pid in confirmed
                or pid in absent_delegator_pids
            ):
                continue
            extra.add(pid)
        return frozenset(extra)

    def _get_present_partner_ids(self, convocable_partner_ids=None):
        """Distinct ``res.partner`` ids counted for quorum presence (people only).

        **Single entry point** for “who is present” for quorum: every stored quorum
        field and check must derive counts from this set (or its length), not from
        vote lines or ``partner.vote`` magnitudes.

        **A — Confirmed attendees:** ``partner_id`` of rows with
        ``attendee_state == confirmed``.

        **B — Represented delegators:** partners in the convocation domain who are
        *not* in A, are *not* ``absent`` on an attendee row, and appear as
        ``delegation.partner_id`` on at least one confirmed, quorum-effective
        delegation (delegate is a confirmed attendee); partial ``vote_type_ids`` still
        counts one person.

        Returns ``frozenset(A | B)`` (set union ⇒ each partner at most once).
        Cancelled assemblies → empty frozenset.

        Does not read ``partner.vote`` nor ``assembly.attendee.vote`` totals.

        :param convocable_partner_ids: optional ``frozenset`` of convocable partner ids
            (same pool as :meth:`_present_quorum_convocable_partner_ids`). When passed
            from :meth:`_compute_quorum`, avoids a second ``res.partner`` search.
        """
        self.ensure_one()
        if self.assembly_state == "cancelled":
            return frozenset()
        confirmed = self._present_quorum_confirmed_attendee_partner_ids()
        if convocable_partner_ids is not None:
            convocable = convocable_partner_ids
        else:
            convocable = self._present_quorum_convocable_partner_ids()
        represented = self._present_quorum_represented_delegator_partner_ids(
            confirmed, convocable
        )
        return frozenset(confirmed | represented)

    def _assembly_ensure_active_for_operational_views(self):
        if self.filtered(lambda a: not a.active):
            raise UserError(
                self.env._(
                    "Operational lists and shortcuts are not available for archived "
                    "assemblies. Unarchive the assembly first."
                )
            )

    def _action_open_related(self, res_model, title):
        self.ensure_one()
        self._assembly_ensure_active_for_operational_views()
        return {
            "type": "ir.actions.act_window",
            "name": title,
            "res_model": res_model,
            "view_mode": "list,form",
            "target": "current",
            "domain": [("assembly_id", "=", self.id)],
            "context": {"default_assembly_id": self.id},
        }

    def action_announce(self):
        return self._transition_assembly_state("announced")

    def action_start_session(self):
        return self._transition_assembly_state("in_session")

    def action_open_live_voting_dashboard(self):
        self.ensure_one()
        self._assembly_ensure_active_for_operational_views()
        if self.assembly_state != "in_session":
            raise UserError(
                self.env._(
                    "The live voting screen is only available while the "
                    "assembly is in session."
                )
            )
        agendas = self.agenda_ids.sorted(lambda a: (a.sequence, a.id))
        if not agendas:
            raise UserError(
                self.env._(
                    "No agenda item is ready for live voting. Open an item from "
                    "the agenda list."
                )
            )
        for agenda in agendas:
            open_v = agenda.voting_ids.filtered(lambda v: v.voting_state == "open")
            if open_v:
                v0 = open_v[0]
                v0._ensure_roll_call_lines()
                return v0.action_open_session_control()
        # Walk through every agenda item (including no-vote) from the first one.
        return agendas[0].action_open_live_voting_screen()

    def action_close(self):
        return self._transition_assembly_state(
            "closed", {"date_end": fields.Datetime.now()}
        )

    def action_cancel(self):
        return self._transition_assembly_state("cancelled", {"date_end": False})

    def action_reopen(self):
        return self._transition_assembly_state("draft", {"date_end": False})

    def action_reopen_from_closed(self):
        self.ensure_one()
        if self.assembly_state != "closed":
            raise UserError(
                self.env._("This action is only available when the assembly is closed.")
            )
        if not self.env.user.has_group("base_assembly.assembly_group_manager"):
            raise UserError(
                self.env._("Only assembly managers can reopen a closed assembly.")
            )
        self.message_post(
            body=self.env._("Assembly reopened from closed (session restored)."),
            message_type="notification",
        )
        return self.with_context(**{CTX_ASSEMBLY_REOPEN_FROM_CLOSED: True}).write(
            {"assembly_state": "in_session"}
        )

    def action_open_header_actions_wizard(self):
        self.ensure_one()
        self._assembly_ensure_active_for_operational_views()
        wiz = self.env["assembly.assembly.header.actions.wizard"].create(
            {"assembly_id": self.id}
        )
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Actions"),
            "res_model": wiz._name,
            "res_id": wiz.id,
            "view_mode": "form",
            "target": "new",
        }

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
            self.env["assembly.attendee"].sudo().create(
                [
                    {"assembly_id": self.id, "partner_id": partner.id}
                    for partner in to_create
                ]
            )
        if self.attendee_ids:
            self.attendee_ids._sync_attendance_link_trackers()
            self.env["assembly.attendee"].recompute_votes(self.attendee_ids)

    def action_recompute_attendee_votes(self):
        """Recompute stored vote lines for all attendees."""
        self.ensure_one()
        self.env["assembly.assembly"]._assembly_raise_if_closed(self)
        if not self.attendee_ids:
            return True
        self.env["assembly.attendee"].recompute_votes(self.attendee_ids)
        return True

    def _get_manual_yes_no_possible_vote_units(self):
        """Vote units held by confirmed attendees for the configured types.

        Sum of stored ``assembly.attendee.vote`` ``attendee_vote_total`` for
        ``attendee_state=confirmed`` and ``vote_type_id in assembly.vote_type_ids``.
        Used to validate manual yes/no counters. Returns ``0.0`` when the
        universe cannot be computed (no confirmed attendees or no vote types).
        """
        self.ensure_one()
        attendee_model = self.env["assembly.attendee"]
        attendee_vote_model = self.env["assembly.attendee.vote"]
        attendees = attendee_model._search_attendees_for_assembly(
            self.id, attendee_state="confirmed"
        )
        vt_ids = self.vote_type_ids.ids
        if not attendees or not vt_ids:
            return 0.0
        lines = attendee_vote_model.search(
            [
                ("attendee_id", "in", attendees.ids),
                ("vote_type_id", "in", vt_ids),
            ]
        )
        return float(sum(lines.mapped("attendee_vote_total")))

    def _render_assembly_doc_html(self, field_name):
        """Render a per-assembly document text with inline_template placeholders.

        Read under the current language, so callers that switch language
        (``assembly.with_context(lang=...)``) get the text in that language and
        generated documents come out in each recipient's language.
        """
        self.ensure_one()
        src = self[field_name]
        if is_html_empty(src):
            return Markup("")
        rendered = self.env["mail.render.mixin"]._render_template(
            str(src), self._name, [self.id], engine="inline_template"
        )[self.id]
        return Markup(rendered or "")

    def get_rendered_publication(self):
        """Convocation HTML rendered from the assembly convocation text."""
        self.ensure_one()
        return self._render_assembly_doc_html("description")

    def get_rendered_publication_text(self):
        """String form of :meth:`get_rendered_publication`."""
        self.ensure_one()
        return str(self.get_rendered_publication())

    def get_rendered_delegation_document_text(self):
        self.ensure_one()
        return self._render_assembly_doc_html("delegation_document_text")

    def get_rendered_delegation_footer_text(self):
        self.ensure_one()
        return self._render_assembly_doc_html("delegation_footer_text")

    def get_rendered_representation_document_text(self):
        self.ensure_one()
        return self._render_assembly_doc_html("representation_document_text")

    def get_rendered_ballot_intro_text(self):
        self.ensure_one()
        return self._render_assembly_doc_html("ballot_intro_text")

    def get_rendered_ballot_nominative_intro_text(self):
        self.ensure_one()
        return self._render_assembly_doc_html("ballot_nominative_intro_text")

    def get_rendered_final_text(self):
        self.ensure_one()
        return self._render_assembly_doc_html("final_text")

    def get_rendered_delegation(self):
        """Delegation HTML: document introduction followed by the footer."""
        self.ensure_one()
        body = self.get_rendered_delegation_document_text()
        foot = self.get_rendered_delegation_footer_text()
        return (
            Markup('<div class="o_assembly_delegation_bundle">')
            + Markup('<div class="o_assembly_delegation_intro">')
            + body
            + Markup("</div>")
            + Markup('<div class="o_assembly_delegation_footer">')
            + foot
            + Markup("</div></div>")
        )

    def action_open_communication_send_wizard(self):
        self.ensure_one()
        preferred_kind = self.env.context.get("default_primary_message_kind")
        ctx = clean_context(self.env.context)
        ctx.setdefault("default_assembly_id", self.id)
        ctx["default_primary_message_kind"] = preferred_kind or "publication"
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Send communication"),
            "res_model": "assembly.communication.send.wizard",
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }

    def action_open_ballot_print_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Generate voting ballots"),
            "res_model": "assembly.ballot.print.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_assembly_id": self.id},
        }

    def action_mail_compose_publication(self):
        self.ensure_one()
        return self.with_context(
            default_primary_message_kind="publication",
        ).action_open_communication_send_wizard()

    def action_mail_compose_ballot_intro(self):
        self.ensure_one()
        return self.with_context(
            default_primary_message_kind="ballot_intro",
        ).action_open_communication_send_wizard()

    def action_mail_compose_delegation(self):
        self.ensure_one()
        return self.with_context(
            default_primary_message_kind="delegation",
        ).action_open_communication_send_wizard()

    def action_open_assembly_outbound_mails(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Outgoing emails"),
            "res_model": "mail.mail",
            "view_mode": "list,form",
            "domain": [
                ("model", "=", "assembly.assembly"),
                ("res_id", "=", self.id),
            ],
            "context": {"create": False, "edit": False},
        }

    def action_open_document_preview_wizard(self):
        self.ensure_one()
        wiz = self.env["assembly.document.preview.wizard"].create(
            {
                "assembly_id": self.id,
                "document_type": self.env.context.get(
                    "default_preview_document_type", "publication"
                ),
            }
        )
        return wiz.action_refresh_preview()

    def action_open_agenda_items(self):
        self.ensure_one()
        self._assembly_ensure_active_for_operational_views()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Agenda items"),
            "res_model": "assembly.agenda",
            "view_mode": "list,kanban,graph,pivot,form",
            "target": "current",
            "domain": [("assembly_id", "=", self.id)],
            "context": {"default_assembly_id": self.id},
        }

    def action_open_votings(self):
        """Open all votings for this assembly (list + form)."""
        self.ensure_one()
        self._assembly_ensure_active_for_operational_views()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Votings"),
            "res_model": "assembly.voting",
            "view_mode": "list,kanban,graph,pivot,form",
            "target": "current",
            "domain": [("assembly_id", "=", self.id)],
        }

    def action_open_delegations(self):
        return self._action_open_related(
            "assembly.delegation", self.env._("Delegations")
        )

    def action_open_representations(self):
        return self._action_open_related(
            "assembly.representation", self.env._("Representations")
        )

    def action_open_attendees(self):
        return self._action_open_related("assembly.attendee", self.env._("Attendees"))

    def action_open_attendance_links(self):
        self.ensure_one()
        self._assembly_ensure_active_for_operational_views()
        ctx = dict(self.env.context)
        ctx.update(
            {
                "default_assembly_id": self.id,
                "search_default_filter_attendance_tracked_link": 1,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Attendees (tracked links & QR)"),
            "res_model": "assembly.attendee",
            "view_mode": "list,form",
            "target": "current",
            "domain": [("assembly_id", "=", self.id)],
            "context": ctx,
        }
