# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Legal/physical representation at an assembly (titular + agent).

Not vote delegation: separate from ``assembly.delegation`` and its business rules.
"""

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .assembly_mixin import assembly_safe_report_filename


class AssemblyRepresentation(models.Model):
    _name = "assembly.representation"
    _description = "Assembly representation"
    _order = "assembly_id, owner_partner_id"

    def _get_report_base_filename(self):
        self.ensure_one()
        owner = assembly_safe_report_filename(
            self.owner_partner_id.display_name, default=self.env._("Represented")
        )
        agent = assembly_safe_report_filename(
            self.agent_partner_id.display_name, default=self.env._("Representative")
        )
        asm = assembly_safe_report_filename(
            self.assembly_id.display_name, default=self.env._("Assembly")
        )
        return f"{asm} - {owner} - {agent}"

    assembly_id = fields.Many2one(
        "assembly.assembly",
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
    owner_partner_id = fields.Many2one(
        "res.partner",
        string="Represented member",
        required=True,
        ondelete="restrict",
        index=True,
    )
    allowed_owner_partner_ids = fields.Many2many(
        "res.partner",
        string="Allowed represented members",
        compute="_compute_allowed_owner_partner_ids",
        help="Partners convocable to the assembly.",
    )
    agent_partner_id = fields.Many2one(
        "res.partner",
        string="Representative (agent)",
        required=True,
        ondelete="restrict",
        index=True,
    )
    active = fields.Boolean(default=True)
    notes = fields.Text(
        help="Optional remarks for this representation record.",
    )

    _sql_constraints = [
        (
            "assembly_representation_assembly_owner_uniq",
            "UNIQUE(owner_partner_id, assembly_id)",
            "Each represented member may have only one representation per assembly.",
        ),
    ]

    @api.depends("assembly_id")
    def _compute_allowed_owner_partner_ids(self):
        partner_model = self.env["res.partner"]
        for record in self:
            if record.assembly_id:
                record.allowed_owner_partner_ids = partner_model.search(
                    record.assembly_id._get_partner_domain()
                )
            else:
                record.allowed_owner_partner_ids = partner_model.browse()

    @api.constrains("assembly_id", "owner_partner_id")
    def _check_owner_is_convocable(self):
        for record in self:
            if not record.assembly_id or not record.owner_partner_id:
                continue
            convocable = self.env["res.partner"].search(
                record.assembly_id._get_partner_domain()
            )
            if record.owner_partner_id not in convocable:
                raise ValidationError(
                    self.env._(
                        "The represented member must be included in the "
                        "convocable partners of the assembly."
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        assemblies = (
            self.env["assembly.assembly"]
            .browse({v["assembly_id"] for v in vals_list if v.get("assembly_id")})
            .exists()
        )
        assemblies._assembly_ensure_not_closed_for_related_changes()
        return super().create(vals_list)

    def write(self, vals):
        self.mapped("assembly_id")._assembly_ensure_not_closed_for_related_changes()
        return super().write(vals)

    def unlink(self):
        self.mapped("assembly_id")._assembly_ensure_not_closed_for_related_changes()
        return super().unlink()
