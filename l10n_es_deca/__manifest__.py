# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "DECA - Documento Electrónico de Control Administrativo",
    "summary": (
        "Transport control document (DECA) with QR-enabled PDF "
        "and public token-based access"
    ),
    "version": "18.0.1.0.0",
    "category": "Localization/Spain",
    "website": "https://www.moval.es",
    "author": "Moval Agroingeniería",
    "maintainers": ["Moval Agroingeniería"],
    "license": "AGPL-3",
    "depends": [
        "base",
        "mail",
        "web",
    ],
    "data": [
        "security/deca_security.xml",
        "security/ir.model.access.csv",
        "data/deca_sequence.xml",
        "report/deca_report.xml",
        "report/deca_templates.xml",
        "wizards/deca_revise_views.xml",
        "views/deca_version_views.xml",
        "views/deca_document_views.xml",
        "views/deca_menus.xml",
    ],
}
