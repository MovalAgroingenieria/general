# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AssemblyType(models.Model):
    _name = "assembly.type"
    _description = "Assembly type"
    _order = "name"

<<<<<<< HEAD
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
=======
>>>>>>> origin/18.0
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
    default_city = fields.Char(string="Default city")
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
<<<<<<< HEAD
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
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "assembly_type_code_company_uniq",
            "UNIQUE(company_id, code)",
            "The code must be unique per company.",
        ),
=======
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_uniq", "UNIQUE(code)", "The code must be unique."),
>>>>>>> origin/18.0
    ]
