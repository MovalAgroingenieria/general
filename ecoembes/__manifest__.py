# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Ecoembes",
    "summary": "Add Ecoembes contribution management",
    "author": "Moval Agroingeniería",
    "license": "AGPL-3",
    "category": "Tools",
    "version": "18.0.1.0.0",
    "depends": ["account"],
    "data": [
        "data/product_material.xml",
        "data/product_submaterial.xml",
        "data/submaterial_types.xml",
        "security/groups.xml",
        "security/ir.model.access.csv",
        "views/product_material_view.xml",
        "views/product_submaterial_view.xml",
        "views/submaterial_type_view.xml",
        "views/product_template_view.xml",
        "views/menu.xml",
        "views/product_component_line_view.xml",
        "wizard/scrap_annual_report_wizard_view.xml",
        "report/report_invoice_scrap_notice.xml",
        "report/scrap_annual_report.xml",
    ],
}
