# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # Monetary in company currency (more correct than a plain Float in €)
    scrap_contribution_total = fields.Monetary(
        string="Total SCRAP Contribution",
        compute="_compute_scrap_contribution_total",
        currency_field="company_currency_id",
        store=False,
    )

    @api.depends(
        "invoice_line_ids.product_id",
        "invoice_line_ids.product_id.product_tmpl_id",
        "invoice_line_ids.quantity",
    )
    def _compute_scrap_contribution_total(self):
        """
        Compute the total SCRAP contribution per invoice.

        - Only lines whose product template is 'manufactured' are considered.
        - Each manufactured product template has 0..n component lines
          (model: material.component.line) that carry:
            * weight_grams
            * submaterial_type_id.fee_per_kg
        - Per invoice line, we sum (weight_kg * fee_per_kg) for all components,
          then multiply by the line quantity.
        - Batched: all component lines for all templates present in the invoice
          are fetched in one search to avoid N+1 lookups.
        """
        component_model = self.env["material.component.line"]

        for move in self:
            total = 0.0

            # 1) Collect all product templates in this invoice that are manufactured
            invoice_lines = move.invoice_line_ids.filtered(lambda li: li.product_id)

            # Create mapping and filter manufactured templates in one step
            manufactured_templates = set()
            template_by_line = {}

            for line in invoice_lines:
                template = line.product_id.product_tmpl_id
                template_by_line[line.id] = template
                if getattr(template, "is_manufactured", False):
                    manufactured_templates.add(template.id)

            if not manufactured_templates:
                move.scrap_contribution_total = 0.0
                continue

            # 2) Batch fetch component lines and process fees
            component_lines = component_model.search(
                [("product_tmpl_id", "in", list(manufactured_templates))]
            )

            # Get all unique submaterial type IDs
            submaterial_ids = {
                comp.submaterial_type_id.id
                for comp in component_lines
                if comp.submaterial_type_id
            }

            # Batch read fees of submaterial types
            fee_by_submaterial = self._get_submaterial_fees(submaterial_ids)

            # Calculate fee per template
            fee_per_template = self._calculate_template_fees(
                component_lines, fee_by_submaterial
            )

            # 5) Sum for each invoice line
            total = self._calculate_total_contribution(
                invoice_lines,
                template_by_line,
                manufactured_templates,
                fee_per_template,
            )

            move.scrap_contribution_total = total

    def _get_submaterial_fees(self, submaterial_ids):
        """Get fee_per_kg for submaterial types in batch."""
        if not submaterial_ids:
            return {}

        fee_by_submaterial = {}
        submaterial_records = self.env["submaterial.type"].browse(submaterial_ids)

        for submaterial in submaterial_records:
            fee_by_submaterial[submaterial.id] = float(
                getattr(submaterial, "fee_per_kg", 0.0) or 0.0
            )

        return fee_by_submaterial

    def _calculate_template_fees(self, component_lines, fee_by_submaterial):
        """Calculate fee per product template based on component lines."""
        fee_per_template = {}

        for comp in component_lines:
            tmpl_id = comp.product_tmpl_id.id
            if not tmpl_id:
                continue

            weight_kg = float(comp.weight_grams or 0.0) / 1000.0
            fee_per_kg = (
                fee_by_submaterial.get(comp.submaterial_type_id.id, 0.0)
                if comp.submaterial_type_id
                else 0.0
            )

            fee_per_template[tmpl_id] = fee_per_template.get(tmpl_id, 0.0) + (
                weight_kg * fee_per_kg
            )

        return fee_per_template

    def _calculate_total_contribution(
        self, invoice_lines, template_by_line, manufactured_templates, fee_per_template
    ):
        """Calculate total SCRAP contribution for all invoice lines."""
        total = 0.0

        for line in invoice_lines:
            template = template_by_line.get(line.id)
            if not template or template.id not in manufactured_templates:
                continue

            unit_fee = fee_per_template.get(template.id, 0.0)
            if unit_fee:
                total += unit_fee * float(line.quantity or 0.0)

        return total
