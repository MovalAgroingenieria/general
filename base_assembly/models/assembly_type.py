# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AssemblyType(models.Model):
    _name = "assembly.type"
    _description = "Assembly type"
    _order = "name"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    description = fields.Text(translate=True)
    vote_type_ids = fields.Many2many(
        "vote.type",
        "assembly_type_vote_type_rel",
        "assembly_type_id",
        "vote_type_id",
        string="Vote types",
        domain=[("active", "=", True)],
    )
    default_quorum_type = fields.Selection(
        [("percentage", "Percentage"), ("fixed", "Fixed number")],
        string="Quorum (1st call)",
        default="percentage",
    )
    default_quorum_value = fields.Float(string="Quorum value (1st call)", default=50.0)
    default_quorum_second_call_type = fields.Selection(
        [("percentage", "Percentage"), ("fixed", "Fixed number"), ("any", "Any")],
        string="Quorum (2nd call)",
        default="any",
    )
    default_quorum_second_call_value = fields.Float(
        string="Quorum value (2nd call)", default=0.0
    )
    partner_domain = fields.Text(
        string="Partner domain",
        default="[]",
        help="Default domain for convocable partners.",
    )
    default_street = fields.Char(string="Default street")
    default_city = fields.Char(
        string="Default city (manual)",
        help="Free text default when not using the city directory.",
    )
    default_city_id = fields.Many2one(
        "res.city",
        string="Default city (directory)",
        ondelete="set null",
        domain="[('country_id', '=?', default_country_id), ('state_id', '=?', default_state_id)]",
    )
    default_zip = fields.Char(string="Default zip")
    default_state_id = fields.Many2one(
        "res.country.state",
        string="Default state",
        ondelete="restrict",
    )
    default_country_id = fields.Many2one(
        "res.country",
        string="Default country",
        ondelete="restrict",
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
        string="Default: require TIN to confirm attendance",
        default=False,
        help=(
            "When creating an assembly from this type, copy this to the assembly. "
            "If enabled, confirming an attendee is blocked when the member has no TIN "
            "or uses the exempt placeholder."
        ),
    )
    default_attendance_partner_vat_format_strict = fields.Boolean(
        string="Default: strict TIN format for attendance confirmation",
        default=False,
        help=(
            "When creating an assembly from this type, copy this to the assembly. "
            "If enabled together with the requirement above, the TIN must pass a "
            "light normalized format check (alphanumeric, length)."
        ),
    )
    require_vat = fields.Boolean(
        string="Require VAT to confirm attendance",
        default=False,
        help=(
            "If enabled, confirming an assembly attendee is blocked when the member "
            "has no tax identification number (VAT/TIN) or only the exempt placeholder."
        ),
    )
    default_allow_attendance_notes = fields.Boolean(
        string="Default: allow attendance annotations",
        default=True,
        help="When creating an assembly from this type, copy this to the assembly.",
    )
    default_include_qr_code = fields.Boolean(
        string="Default: add QR code (tracked attendance link)",
        default=True,
        help=(
            "When creating an assembly from this type, copy this to the assembly. "
            "If disabled, attendee short links for QR are not created."
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

    _sql_constraints = [
        (
            "assembly_type_code_company_uniq",
            "UNIQUE(company_id, code)",
            "The code must be unique per company.",
        ),
    ]
