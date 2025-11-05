# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime


class ScrapAnnualReportWizard(models.TransientModel):
    _name = 'scrap.annual.report.wizard'
    _description = 'SCRAP Annual Report Wizard'

    year = fields.Integer(
        string='Year',
        required=True,
        default=lambda self: datetime.now().year,
        help='Select the year for the SCRAP contribution report'
    )

    def print_report(self):
        """Generate and return the SCRAP annual report."""
        self.ensure_one()
        report_data = self._get_report_data()

        if not report_data:
            raise UserError(_(
                'No SCRAP contributions found for year %s.'
            ) % self.year)

        # Pass data directly as individual parameters
        data = {
            'year': self.year,
            'report_data': report_data
        }
        report_ref = self.env.ref('ecoembes.action_report_scrap_annual')
        return report_ref.report_action(None, data=data)

    def _get_report_data(self):
        """Calculate SCRAP contributions grouped by material/submaterial."""
        self.ensure_one()

        # Date range for the year
        date_from = f'{self.year}-01-01'
        date_to = f'{self.year}-12-31'

        # Find all customer invoices in the year that are posted
        invoices = self.env['account.move'].search([
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
        ])

        # Dictionary to accumulate data by submaterial type
        submaterial_data = {}

        for invoice in invoices:
            sign = 1 if invoice.move_type == 'out_invoice' else -1

            for line in invoice.invoice_line_ids:
                product = line.product_id
                if not product or not product.product_tmpl_id.is_manufactured:
                    continue

                # Get component lines for this product
                components = self.env['material.component.line'].search([
                    ('product_tmpl_id', '=', product.product_tmpl_id.id)
                ])

                for component in components:
                    if not component.submaterial_type_id:
                        continue

                    submaterial_type = component.submaterial_type_id
                    key = (
                        submaterial_type.id,
                        submaterial_type.submaterial_id.material_id.name,
                        submaterial_type.submaterial_id.name,
                        submaterial_type.name,
                    )

                    if key not in submaterial_data:
                        mat_id = submaterial_type.submaterial_id.material_id
                        material_name = mat_id.name
                        submaterial_name = submaterial_type.submaterial_id.name
                        submaterial_data[key] = {
                            'material_name': material_name,
                            'submaterial_name': submaterial_name,
                            'submaterial_type_name': submaterial_type.name,
                            'fee_per_kg': submaterial_type.fee_per_kg,
                            'total_weight_kg': 0.0,
                            'total_contribution': 0.0,
                        }

                    # Calculate weight and contribution for this line
                    weight_kg = (component.weight_grams / 1000.0) * \
                        line.quantity * sign
                    contribution = weight_kg * submaterial_type.fee_per_kg

                    submaterial_data[key]['total_weight_kg'] += weight_kg
                    submaterial_data[key]['total_contribution'] += contribution

        # Group data by material and submaterial
        grouped_data = {}

        for key, data in submaterial_data.items():
            if data['total_weight_kg'] <= 0:  # Skip negative/zero weights
                continue

            material_name = data['material_name']
            submaterial_name = data['submaterial_name']

            # Create material group if it doesn't exist
            if material_name not in grouped_data:
                grouped_data[material_name] = {
                    'material_name': material_name,
                    'submaterials': {},
                    'total_weight_kg': 0.0,
                    'total_contribution': 0.0,
                }

            # Create submaterial group if it doesn't exist
            mat_submaterials = grouped_data[material_name]['submaterials']
            if submaterial_name not in mat_submaterials:
                mat_submaterials[submaterial_name] = {
                    'submaterial_name': submaterial_name,
                    'types': [],
                    'total_weight_kg': 0.0,
                    'total_contribution': 0.0,
                }

            # Add type data
            mat_submaterials[submaterial_name]['types'].append(data)

            # Update submaterial totals
            sub_data = mat_submaterials[submaterial_name]
            sub_data['total_weight_kg'] += data['total_weight_kg']
            sub_data['total_contribution'] += data['total_contribution']

            # Update material totals
            mat_data = grouped_data[material_name]
            mat_data['total_weight_kg'] += data['total_weight_kg']
            mat_data['total_contribution'] += data['total_contribution']

        # Sort and structure final data
        result = []
        for material_name in sorted(grouped_data.keys()):
            material_data = grouped_data[material_name]

            # Sort submaterials
            submaterials = material_data['submaterials']
            for submaterial_name in sorted(submaterials.keys()):
                submaterial_data = submaterials[submaterial_name]

                # Sort types within submaterial
                submaterial_data['types'].sort(
                    key=lambda x: x['submaterial_type_name']
                )

            result.append(material_data)

        return result

    @api.constrains('year')
    def _check_year(self):
        """Validate year input."""
        # No restrictions yet
