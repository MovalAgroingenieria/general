# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Base Assembly",
    "summary": "Core models for assemblies: agenda, attendees, delegations, voting",
    "version": "18.0.1.9.3",
    "category": "Administration",
    "author": "Moval Agroingeniería",
    "website": "https://www.moval.es",
    "license": "AGPL-3",
    "depends": ["base", "base_vote", "web"],
    "data": [
        "security/assembly_security.xml",
        "security/assembly_group_system.xml",
        "security/ir.model.access.csv",
        "data/assembly_sequence_data.xml",
        "views/assembly_type_views.xml",
        "views/assembly_assembly_views.xml",
        "views/assembly_attendee_views.xml",
        "views/assembly_delegation_views.xml",
        "views/assembly_voting_views.xml",
        "views/res_partner_views.xml",
        "views/menu_views.xml",
        "report/assembly_attendance_reports.xml",
        "report/assembly_delegation_report.xml",
        "report/assembly_representation_report.xml",
        "report/assembly_voting_ballot_reports.xml",
    ],
}
