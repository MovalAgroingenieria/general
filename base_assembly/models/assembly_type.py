# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models

_DEFAULT_PUBLICATION_TEXT = """<h2>{{ object.name }}</h2>
<p>{{ format_datetime(object.date_first_call) if object.date_first_call else '' }}{{ ' — ' + object.location if object.location else '' }}</p>
<p>This notice is the official convocation for the assembly above. Members are requested to attend at the date, time and venue indicated, and to review the agenda.</p>"""

_DEFAULT_DELEGATION_DOCUMENT_TEXT = """<p>Vote delegation form for the assembly <strong>{{ object.name }}</strong>.</p>
<p>Identify the delegator and the delegate below and specify the vote types delegated.</p>"""

_DEFAULT_DELEGATION_FOOTER_TEXT = """<p>The delegator certifies the accuracy of the information above and authorizes the delegate to cast votes on their behalf for the indicated vote type(s).</p>"""

_DEFAULT_REPRESENTATION_DOCUMENT_TEXT = """<p>Representation form for the assembly <strong>{{ object.name }}</strong>.</p>
<p>The represented member appoints the representative below to attend and act on their behalf at this assembly.</p>"""

_DEFAULT_BALLOT_INTRO_TEXT = """<p>Voting ballot for <strong>{{ object.name }}</strong>.</p>
<p>Mark your choice clearly for each agenda item.</p>"""

_DEFAULT_BALLOT_NOMINATIVE_INTRO_TEXT = (
    "<p>Personalized voting ballot for the assembly "
    "<strong>{{ object.name }}</strong>.</p>"
)

_DEFAULT_FINAL_TEXT = (
    "<p>What is set out above is hereby notified for your information "
    "and attendance.</p>"
)


class AssemblyType(models.Model):
    _name = "assembly.type"
    _description = "Assembly type"
    _order = "name"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    default_publication_text = fields.Html(
        string="Default convocation text",
        sanitize=False,
        translate=True,
        default=_DEFAULT_PUBLICATION_TEXT,
        help="Copied to the convocation text of new assemblies of this type. "
        "Supports placeholders such as {{ object.name }}.",
    )
    default_delegation_document_text = fields.Html(
        string="Default delegation document",
        sanitize=False,
        translate=True,
        default=_DEFAULT_DELEGATION_DOCUMENT_TEXT,
    )
    default_delegation_footer_text = fields.Html(
        string="Default delegation footer",
        sanitize=False,
        translate=True,
        default=_DEFAULT_DELEGATION_FOOTER_TEXT,
    )
    default_representation_document_text = fields.Html(
        string="Default representation document",
        sanitize=False,
        translate=True,
        default=_DEFAULT_REPRESENTATION_DOCUMENT_TEXT,
    )
    default_ballot_intro_text = fields.Html(
        string="Default ballot introduction",
        sanitize=False,
        translate=True,
        default=_DEFAULT_BALLOT_INTRO_TEXT,
    )
    default_ballot_nominative_intro_text = fields.Html(
        string="Default nominative ballot introduction",
        sanitize=False,
        translate=True,
        default=_DEFAULT_BALLOT_NOMINATIVE_INTRO_TEXT,
    )
    default_final_text = fields.Html(
        string="Default final text",
        sanitize=False,
        translate=True,
        default=_DEFAULT_FINAL_TEXT,
    )
    vote_type_ids = fields.Many2many(
        "vote.type",
        "assembly_type_vote_type_rel",
        "assembly_type_id",
        "vote_type_id",
        string="Vote types",
        domain=[("active", "=", True)],
    )
    partner_domain = fields.Text(
        string="Partner domain",
        default="[]",
        help="Default domain for convocable partners.",
    )
    default_street = fields.Char(
        string="Default street",
        default=lambda self: self.env.company.street,
    )
    default_city = fields.Char(
        string="Default city (manual)",
        default=lambda self: self.env.company.city,
        help="Free text default when not using the city directory.",
    )
    default_city_id = fields.Many2one(
        "res.city",
        string="Default city (directory)",
        ondelete="set null",
        domain="[('country_id', '=?', default_country_id), "
        "('state_id', '=?', default_state_id)]",
    )
    default_zip = fields.Char(
        string="Default zip",
        default=lambda self: self.env.company.zip,
    )
    default_state_id = fields.Many2one(
        "res.country.state",
        string="Default state",
        ondelete="restrict",
        default=lambda self: self.env.company.state_id,
    )
    default_country_id = fields.Many2one(
        "res.country",
        string="Default country",
        ondelete="restrict",
        default=lambda self: self.env.company.country_id,
    )
    default_president_id = fields.Many2one(
        "res.users",
        string="Default president",
        ondelete="set null",
    )
    default_secretary_id = fields.Many2one(
        "res.users",
        string="Default secretary",
        ondelete="set null",
    )
    default_attendance_require_partner_vat_confirm = fields.Boolean(
        string="Default: require TIN to mark attended",
        default=False,
        help=(
            "When creating an assembly from this type, copy this to the assembly. "
            "If enabled, recording a member as attended is blocked when the member has "
            "no TIN or uses the exempt placeholder."
        ),
    )
    default_attendance_partner_vat_format_strict = fields.Boolean(
        string="Default: strict TIN format when marking attended",
        default=False,
        help=(
            "When creating an assembly from this type, copy this to the assembly. "
            "If enabled together with the requirement above, the TIN must pass a "
            "light normalized format check (alphanumeric, length)."
        ),
    )
    default_allow_attendance_notes = fields.Boolean(
        string="Default: allow attendance annotations",
        default=True,
        help="When creating an assembly from this type, copy this to the assembly.",
    )
    default_include_qr_code = fields.Boolean(
        string="Default: tracked attendance links & QR",
        default=True,
        help=(
            "Copied to new assemblies of this type. When enabled, managers get per-"
            "attendee short URLs (opens counted) and QR actions on each attendee; the "
            "assembly form shows the Links & QR smart button. When disabled, trackers "
            "are not created for new assemblies using this default."
        ),
    )
    active = fields.Boolean(default=True)

    @api.model
    def _assembly_type_apply_default_city_id_to_vals(self, vals):
        cid = vals.get("default_city_id")
        if not cid:
            return
        city = self.env["res.city"].browse(cid)
        if not city.exists():
            return
        vals.setdefault("default_city", city.name)
        if city.zipcode:
            vals.setdefault("default_zip", city.zipcode)
        if city.state_id:
            vals.setdefault("default_state_id", city.state_id.id)
        if city.country_id:
            vals.setdefault("default_country_id", city.country_id.id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._assembly_type_apply_default_city_id_to_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        self._assembly_type_apply_default_city_id_to_vals(vals)
        return super().write(vals)

    @api.onchange("company_id")
    def _onchange_company_id_address_defaults(self):
        company = self.company_id
        if not company:
            return
        self.default_street = company.street
        self.default_city = company.city
        self.default_city_id = False
        self.default_zip = company.zip
        self.default_state_id = company.state_id
        self.default_country_id = company.country_id

    @api.onchange("default_country_id")
    def _onchange_assembly_type_default_country_id(self):
        if (
            self.default_state_id
            and self.default_country_id
            and self.default_state_id.country_id != self.default_country_id
        ):
            self.default_state_id = False
        if (
            self.default_city_id
            and self.default_country_id
            and self.default_city_id.country_id != self.default_country_id
        ):
            self.default_city_id = False

    @api.onchange("default_state_id")
    def _onchange_assembly_type_default_state_id(self):
        if self.default_state_id:
            self.default_country_id = self.default_state_id.country_id

    @api.onchange("default_city_id")
    def _onchange_assembly_type_default_city_id(self):
        if self.default_city_id:
            self.default_city = self.default_city_id.name
            if self.default_city_id.zipcode:
                self.default_zip = self.default_city_id.zipcode
            self.default_state_id = self.default_city_id.state_id
            self.default_country_id = self.default_city_id.country_id

    @api.onchange("default_city")
    def _onchange_assembly_type_default_city_char(self):
        if (
            self.default_city_id
            and (self.default_city or "").strip()
            != (self.default_city_id.name or "").strip()
        ):
            self.default_city_id = False
