# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

try:
    from jinja2 import Template
    from jinja2.exceptions import TemplateError
except ImportError:
    Template = None
    TemplateError = Exception


class AssemblyAssembly(models.Model):
    _name = "assembly.assembly"
    _description = "Assembly"
    _order = "date_first_call desc, id desc"

    name = fields.Char(required=True)
    code = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env._("New"),
    )
    assembly_type_id = fields.Many2one(
        "assembly.type",
        string="Assembly type",
        ondelete="restrict",
    )
    date_announcement = fields.Date(string="Announcement date")
    date_first_call = fields.Datetime(string="First call")
    date_second_call = fields.Datetime(string="Second call")
    date_start = fields.Datetime(string="Session start")
    date_end = fields.Datetime(string="Session end")
    location = fields.Char(help="Short location description")
    # Full address for documents (generic from WUA)
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
    # Publishable / template texts (Jinja2: assembly_day, assembly_month, assembly_year, assembly)
    publication_text = fields.Html(
        string="Publication text",
        help="Rendered in reports; use {{ assembly_day }}, {{ assembly_month }}, {{ assembly_year }}, {{ assembly }}.",
    )
    final_paragraph = fields.Html(
        string="Final paragraph",
        help="Rendered in individual calls; same Jinja2 variables.",
    )
    # Document templates for delegation/representation reports
    delegation_document_text = fields.Html(string="Delegation document text")
    delegation_footer_text = fields.Html(string="Delegation footer text")
    representation_document_text = fields.Html(string="Representation document text")
    representation_footer_text = fields.Html(string="Representation footer text")
    ballot_intro_text = fields.Html(
        string="Ballot intro text",
        help="Shown on voting ballot; use {{ partner }} for nominative ballot.",
    )
    ballot_nominative_intro_text = fields.Html(
        string="Ballot nominative intro text",
        help="Shown on nominative ballot; variables: {{ partner }}, {{ attendee }}.",
    )
    internal_notes = fields.Html(string="Internal notes")
    public_notes = fields.Html(string="Public notes")
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
    is_second_call = fields.Boolean(string="Held in 2nd call", default=False)
    allow_online_voting = fields.Boolean(
        string="Allow online voting",
        default=False,
        help="If set, attendees can cast votes via the portal when the assembly is in session.",
    )
    partner_domain = fields.Text(string="Partner domain", default="[]")
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
    representation_ids = fields.One2many(
        "assembly.representation",
        "assembly_id",
        string="Representations",
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
    active = fields.Boolean(default=True)
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

    @api.depends("agenda_ids", "delegation_ids", "representation_ids")
    def _compute_counts(self):
        for rec in self:
            rec.count_agenda_items = len(rec.agenda_ids)
            rec.count_delegations = len(rec.delegation_ids)
            rec.count_representations = len(rec.representation_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code", self.env._("New")) == self.env._("New"):
                vals["code"] = self.env["ir.sequence"].next_by_code(
                    "assembly.assembly"
                ) or self.env._("New")
            # Apply type defaults on create (onchange does not run on create)
            if vals.get("assembly_type_id"):
                atype = self.env["assembly.type"].browse(vals["assembly_type_id"])
                if atype.exists():
                    if "quorum_type" not in vals:
                        vals["quorum_type"] = atype.default_quorum_type
                    if "quorum_value" not in vals:
                        vals["quorum_value"] = atype.default_quorum_value
                    if "vote_type_ids" not in vals and atype.vote_type_ids:
                        vals["vote_type_ids"] = [(6, 0, atype.vote_type_ids.ids)]
        return super().create(vals_list)

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

    @api.depends(
        "partner_domain",
        "attendee_ids",
        "attendee_ids.attendee_state",
        "delegation_ids",
        "delegation_ids.delegation_state",
        "quorum_type",
        "quorum_value",
        "quorum_second_call_type",
        "quorum_second_call_value",
        "is_second_call",
    )
    def _compute_quorum(self):
        for assembly in self:
            try:
                domain = safe_eval(
                    assembly.partner_domain or "[]", {"__builtins__": {}}
                )
            except (TypeError, ValueError, SyntaxError, MemoryError):
                domain = []
            partners = self.env["res.partner"].search(domain)
            assembly.total_possible_attendees = len(partners)
            present = assembly.count_present_attendees()
            assembly.total_present_attendees = present
            if assembly.total_possible_attendees <= 0:
                assembly.quorum_percentage = 0.0
                assembly.quorum_reached = False
            else:
                assembly.quorum_percentage = (
                    present / assembly.total_possible_attendees * 100.0
                )
                if assembly.is_second_call:
                    qtype = assembly.quorum_second_call_type
                    qval = assembly.quorum_second_call_value
                else:
                    qtype = assembly.quorum_type
                    qval = assembly.quorum_value
                if qtype == "any":
                    assembly.quorum_reached = present > 0
                elif qtype == "percentage":
                    assembly.quorum_reached = assembly.quorum_percentage >= qval
                else:
                    assembly.quorum_reached = present >= qval

    def count_present_attendees(self):
        """Count distinct partners that are present (confirmed or represented)."""
        self.ensure_one()
        confirmed_attendees = self.attendee_ids.filtered(
            lambda a: a.attendee_state == "confirmed"
        )
        confirmed_partner_ids = set(confirmed_attendees.mapped("partner_id").ids)
        # Partners represented by an agent who is confirmed
        for rep in self.representation_ids.filtered(
            lambda r: r.representation_state == "confirmed"
        ):
            if rep.agent_id in confirmed_attendees.mapped("partner_id"):
                confirmed_partner_ids.add(rep.partner_id.id)
        # Delegators represented by a confirmed delegatee
        for d in self.delegation_ids.filtered(
            lambda x: x.delegation_state == "confirmed"
        ):
            if d.delegate_partner_id in confirmed_attendees.mapped("partner_id"):
                confirmed_partner_ids.add(d.partner_id.id)
        return len(confirmed_partner_ids)

    def action_announce(self):
        self.ensure_one()
        if self.assembly_state != "draft":
            raise UserError(self.env._("Only draft assemblies can be announced."))
        if not self.agenda_ids:
            raise UserError(
                self.env._("Add at least one agenda item before announcing.")
            )
        self.assembly_state = "announced"

    def action_open_registration(self):
        self.ensure_one()
        if self.assembly_state != "announced":
            raise UserError(
                self.env._("Only announced assemblies can open registration.")
            )
        self.assembly_state = "open"

    def action_start_session(self):
        self.ensure_one()
        if self.assembly_state != "open":
            raise UserError(self.env._("Only open assemblies can start session."))
        self.write(
            {"assembly_state": "in_session", "date_start": fields.Datetime.now()}
        )
        if not self.quorum_reached:
            return {
                "warning": {
                    "title": self.env._("Quorum not reached"),
                    "message": self.env._(
                        "Quorum is not reached. You can still start the session."
                    ),
                }
            }
        return True

    def action_close(self):
        self.ensure_one()
        if self.assembly_state != "in_session":
            raise UserError(self.env._("Only in-session assemblies can be closed."))
        open_votings = self.env["assembly.voting"].search(
            [
                ("agenda_id.assembly_id", "=", self.id),
                ("voting_state", "=", "open"),
            ]
        )
        if open_votings:
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
                self.env._("All agenda items must be voted or skipped before closing.")
            )
        self.write({"assembly_state": "closed", "date_end": fields.Datetime.now()})

    def action_cancel(self):
        self.ensure_one()
        self.env["assembly.voting"].search(
            [
                ("agenda_id.assembly_id", "=", self.id),
                ("voting_state", "=", "open"),
            ]
        ).write({"voting_state": "cancelled"})
        self.assembly_state = "cancelled"

    def action_reopen(self):
        self.ensure_one()
        if self.assembly_state != "cancelled":
            raise UserError(self.env._("Only cancelled assemblies can be reopened."))
        self.attendee_ids.unlink()
        self.representation_ids.unlink()
        votings = self.env["assembly.voting"].search(
            [("agenda_id.assembly_id", "=", self.id)]
        )
        votings.unlink()
        self.agenda_ids.write({"agenda_state": "pending"})
        self.assembly_state = "draft"

    def action_generate_attendees(self):
        self.ensure_one()
        if self.assembly_state not in ("draft", "announced", "open"):
            raise UserError(self.env._("Cannot generate attendees in current state."))
        try:
            domain = safe_eval(self.partner_domain or "[]", {"__builtins__": {}})
        except (TypeError, ValueError, SyntaxError, MemoryError):
            domain = []
        partners = self.env["res.partner"].search(domain)
        if hasattr(partners, "filtered"):
            partners = partners.filtered(
                lambda p: not getattr(p, "assembly_excluded", False)
            )
        existing = self.attendee_ids.mapped("partner_id")
        to_create = partners - existing
        for partner in to_create:
            self.env["assembly.attendee"].create(
                {"assembly_id": self.id, "partner_id": partner.id}
            )

    def action_recompute_attendee_votes(self):
        self.ensure_one()
        self.attendee_ids.recompute_votes()

    def _render_html_template(self, template_str, **extra):
        """Render HTML template with Jinja2. Variables: assembly, assembly_day, assembly_month, assembly_year."""
        if not template_str or not Template:
            return template_str or ""
        lang = self.env.context.get("lang") or "en_US"
        try:
            from babel.dates import format_date
        except ImportError:
            format_date = None
        dt = self.date_first_call or self.date_end or fields.Datetime.now()
        if hasattr(dt, "date"):
            dt = dt.date()
        assembly_day = format_date(dt, "d", locale=lang) if format_date else str(dt.day)
        assembly_month = (
            format_date(dt, "LLLL", locale=lang) if format_date else str(dt.month)
        )
        assembly_year = (
            format_date(dt, "y", locale=lang) if format_date else str(dt.year)
        )
        try:
            t = Template(template_str)
            return t.render(
                assembly=self,
                assembly_day=assembly_day,
                assembly_month=assembly_month,
                assembly_year=assembly_year,
                **extra,
            )
        except TemplateError:
            return template_str or ""

    def get_rendered_publication_text(self):
        return self._render_html_template(self.publication_text or "")

    def get_rendered_final_paragraph(self):
        return self._render_html_template(self.final_paragraph or "")

    def get_rendered_delegation_document_text(self):
        return self._render_html_template(self.delegation_document_text or "")

    def get_rendered_delegation_footer_text(self):
        return self._render_html_template(self.delegation_footer_text or "")

    def get_rendered_representation_document_text(self):
        return self._render_html_template(self.representation_document_text or "")

    def get_rendered_representation_footer_text(self):
        return self._render_html_template(self.representation_footer_text or "")

    def get_rendered_ballot_intro_text(self):
        return self._render_html_template(self.ballot_intro_text or "")

    def get_rendered_ballot_nominative_intro_text(self):
        return self._render_html_template(self.ballot_nominative_intro_text or "")

    def action_preview_publication_text(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Preview publication text"),
            "res_model": "wizard.preview.publicationtext",
            "view_mode": "form",
            "target": "new",
            "context": {"active_id": self.id},
        }

    def action_preview_final_paragraph(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Preview final paragraph"),
            "res_model": "wizard.preview.publicationtext",
            "view_mode": "form",
            "target": "new",
            "context": {"active_id": self.id, "show_final_paragraph": True},
        }

    def action_open_agenda_items(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Agenda items"),
            "res_model": "assembly.agenda",
            "view_mode": "list,form",
            "domain": [("assembly_id", "=", self.id)],
            "context": {"default_assembly_id": self.id},
        }

    def action_open_delegations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Delegations"),
            "res_model": "assembly.delegation",
            "view_mode": "list,form",
            "domain": [("assembly_id", "=", self.id)],
            "context": {"default_assembly_id": self.id},
        }

    def action_open_representations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Representations"),
            "res_model": "assembly.representation",
            "view_mode": "list,form",
            "domain": [("assembly_id", "=", self.id)],
            "context": {"default_assembly_id": self.id},
        }

    def action_open_attendees(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Attendees"),
            "res_model": "assembly.attendee",
            "view_mode": "list,form",
            "domain": [("assembly_id", "=", self.id)],
            "context": {"default_assembly_id": self.id},
        }
