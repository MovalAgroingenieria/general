# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Base Assembly",
    "summary": "Assembly management: agenda, attendance, delegations, voting",
    "version": "18.0.1.0.0",
    "category": "Administration",
    "website": "https://www.moval.es",
    "author": "Moval",
    "license": "AGPL-3",
    "depends": ["base", "base_vote", "web"],
    "data": [
        "security/assembly_security.xml",
        "security/assembly_security_manager_rules.xml",
        "security/ir.model.access.csv",
        "data/assembly_sequence_data.xml",
        "views/assembly_type_views.xml",
        "views/assembly_assembly_views.xml",
        "views/assembly_attendee_views.xml",
        "views/assembly_delegation_views.xml",
        "views/assembly_representation_views.xml",
        "views/assembly_voting_views.xml",
        "views/res_partner_views.xml",
        "views/menu_views.xml",
        "wizard/wizard_preview_publicationtext_view.xml",
        "report/assembly_attendance_reports.xml",
        "report/assembly_delegation_report.xml",
        "report/assembly_representation_report.xml",
        "report/assembly_voting_ballot_reports.xml",
    ],
}
