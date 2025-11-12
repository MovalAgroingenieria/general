# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments

from datetime import date as date_cls
from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class ScrapAnnualReportWizard(models.TransientModel):
    _name = "scrap.annual.report.wizard"
    _description = "SCRAP Annual Report Wizard"

    year = fields.Integer(
        required=True,
        default=lambda self: datetime.now().year,
        help="Year to compute the SCRAP contribution report "
        "for posted customer invoices.",
    )

    def print_report(self):
        """Generate and return the SCRAP annual report."""
        self.ensure_one()
        report_data = self._get_report_data()
        if not report_data:
            raise UserError(
                self.env._("No SCRAP contributions found for year %s.", self.year)
            )

        data = {"year": self.year, "report_data": report_data}
        # Use the wizard record as the target of the report action
        return self.env.ref("ecoembes.action_report_scrap_annual").report_action(
            self, data=data
        )

    # ---------------------------------------------------------------------
    # Core computation
    # ---------------------------------------------------------------------
    def _get_report_data(self):
        """Compute SCRAP contributions grouped by Material > Submaterial > Type."""
        self.ensure_one()

        invoices = self._get_invoices_for_year()
        if not invoices:
            return []

        lines = invoices.mapped("invoice_line_ids")
        manufactured_templates = self._get_manufactured_templates(lines)
        if not manufactured_templates:
            return []

        components_by_template = self._get_components_by_template(
            manufactured_templates
        )
        type_contributions = self._compute_type_contributions(
            invoices, components_by_template
        )
        return self._build_hierarchy(type_contributions)

    def _get_invoices_for_year(self):
        """Get posted customer invoices for the selected year."""
        date_from = f"{self.year}-01-01"
        date_to = f"{self.year}-12-31"

        return self.env["account.move"].search(
            [
                ("company_id", "=", self.env.company.id),
                ("move_type", "in", ["out_invoice", "out_refund"]),
                ("state", "=", "posted"),
                ("invoice_date", ">=", date_from),
                ("invoice_date", "<=", date_to),
            ]
        )

    def _get_manufactured_templates(self, lines):
        """Extract manufactured product templates from invoice lines."""
        template_ids = lines.mapped("product_id.product_tmpl_id")
        return template_ids.filtered("is_manufactured")

    def _get_components_by_template(self, template_ids):
        """Get components grouped by product template."""
        components = self.env["material.component.line"].search(
            [("product_tmpl_id", "in", template_ids.ids)]
        )
        components_by_template = {}
        for comp in components:
            components_by_template.setdefault(comp.product_tmpl_id.id, []).append(comp)
        return components_by_template

    def _compute_type_contributions(self, invoices, components_by_template):
        """Compute contributions per submaterial type."""
        per_type = {}
        for invoice in invoices:
            sign = 1 if invoice.move_type == "out_invoice" else -1
            self._process_invoice_lines(invoice, sign, components_by_template, per_type)
        return per_type

    def _process_invoice_lines(self, invoice, sign, components_by_template, per_type):
        """Process all lines in an invoice and update type contributions."""
        for line in invoice.invoice_line_ids:
            product = line.product_id
            template = product.product_tmpl_id
            if not (product and template and template.is_manufactured):
                continue

            self._process_line_components(
                line, template, sign, components_by_template, per_type
            )

    def _process_line_components(
        self, line, template, sign, components_by_template, per_type
    ):
        """Process all components of a line and update contributions."""
        for comp in components_by_template.get(template.id, []):
            submaterial_type = comp.submaterial_type_id
            if not submaterial_type:
                continue

            self._update_type_contribution(line, comp, submaterial_type, sign, per_type)

    def _update_type_contribution(self, line, comp, submaterial_type, sign, per_type):
        """Update contribution for a specific submaterial type."""
        material_name = submaterial_type.submaterial_id.material_id.name
        submaterial_name = submaterial_type.submaterial_id.name
        key = (
            submaterial_type.id,
            material_name,
            submaterial_name,
            submaterial_type.name,
        )

        bucket = per_type.get(key)
        if not bucket:
            bucket = per_type[key] = {
                "material_name": material_name,
                "submaterial_name": submaterial_name,
                "submaterial_type_name": submaterial_type.name,
                "fee_per_kg": submaterial_type.fee_per_kg or 0.0,
                "total_weight_kg": 0.0,
                "total_contribution": 0.0,
            }

        weight_kg = (comp.weight_grams or 0.0) / 1000.0 * (line.quantity or 0.0) * sign
        contribution = weight_kg * (submaterial_type.fee_per_kg or 0.0)

        bucket["total_weight_kg"] += weight_kg
        bucket["total_contribution"] += contribution

    def _build_hierarchy(self, type_contributions):
        """Build Material > Submaterial > Type hierarchy."""
        grouped = {}
        for key, bucket in type_contributions.items():
            if bucket["total_weight_kg"] <= 0:
                continue

            self._add_to_hierarchy(grouped, key, bucket)

        return self._sort_hierarchy(grouped)

    def _add_to_hierarchy(self, grouped, key, bucket):
        """Add a type contribution to the hierarchy."""
        _st_id, material_name, submaterial_name, _type_name = key

        material_group = grouped.setdefault(
            material_name,
            {
                "material_name": material_name,
                "submaterials": {},
                "total_weight_kg": 0.0,
                "total_contribution": 0.0,
            },
        )

        submaterial_group = material_group["submaterials"].setdefault(
            submaterial_name,
            {
                "submaterial_name": submaterial_name,
                "types": [],
                "total_weight_kg": 0.0,
                "total_contribution": 0.0,
            },
        )

        submaterial_group["types"].append(bucket)
        submaterial_group["total_weight_kg"] += bucket["total_weight_kg"]
        submaterial_group["total_contribution"] += bucket["total_contribution"]
        material_group["total_weight_kg"] += bucket["total_weight_kg"]
        material_group["total_contribution"] += bucket["total_contribution"]

    def _sort_hierarchy(self, grouped):
        """Sort the hierarchy for stable output."""
        result = []
        for material_name in sorted(grouped.keys()):
            material_group = grouped[material_name]
            for submaterial in material_group["submaterials"].values():
                submaterial["types"].sort(key=lambda t: t["submaterial_type_name"])
            result.append(material_group)
        return result

    # ---------------------------------------------------------------------
    # Constraints
    # ---------------------------------------------------------------------
    @api.constrains("year")
    def _check_year(self):
        """Ensure the year is within a reasonable range."""
        current = date_cls.today().year
        for wiz in self:
            if wiz.year < 2000 or wiz.year > current:
                raise ValidationError(
                    wiz.env._("Year must be between 2000 and %s.", current)
                )
