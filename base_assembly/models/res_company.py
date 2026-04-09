# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models

_ASSEMBLY_COMPANY_DEFAULT_CONFIG_REFS = (
    (
        "assembly_default_publication_mail_template_id",
        "base_assembly.mail_template_assembly_publication_default",
    ),
    (
        "assembly_default_delegation_document_mail_template_id",
        "base_assembly.mail_template_assembly_delegation_document_default",
    ),
    (
        "assembly_default_delegation_footer_mail_template_id",
        "base_assembly.mail_template_assembly_delegation_footer_default",
    ),
    (
        "assembly_default_ballot_intro_mail_template_id",
        "base_assembly.mail_template_assembly_ballot_intro_default",
    ),
    (
        "assembly_default_ballot_nominative_intro_mail_template_id",
        "base_assembly.mail_template_assembly_ballot_nominative_intro_default",
    ),
    (
        "assembly_af_publication_fallback_qweb_id",
        "base_assembly.assembly_af_publication_qweb",
    ),
    (
        "assembly_af_delegation_document_fallback_qweb_id",
        "base_assembly.assembly_af_delegation_document_qweb",
    ),
    (
        "assembly_af_delegation_footer_fallback_qweb_id",
        "base_assembly.assembly_af_delegation_footer_qweb",
    ),
    (
        "assembly_af_ballot_intro_fallback_qweb_id",
        "base_assembly.assembly_af_ballot_intro_qweb",
    ),
    (
        "assembly_af_ballot_nominative_intro_fallback_qweb_id",
        "base_assembly.assembly_af_ballot_nominative_intro_qweb",
    ),
    (
        "assembly_attendance_landing_qweb_id",
        "base_assembly.assembly_attendance_landing_page",
    ),
    (
        "assembly_attendance_error_qweb_id",
        "base_assembly.assembly_attendance_error_page",
    ),
)


class ResCompany(models.Model):
    _inherit = "res.company"

    assembly_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Assembly reference sequence",
        domain="[('code', '=', 'assembly.assembly'), '|', "
        "('company_id', '=', False), ('company_id', '=', id)]",
        help="Sequence used to generate assembly reference codes. "
        "If empty, the system falls back to any sequence with code “assembly.assembly”.",
    )
    assembly_default_publication_mail_template_id = fields.Many2one(
        "mail.template",
        string="Default publication mail template",
        domain="[('model', '=', 'assembly.assembly')]",
        help="Used when an assembly has no publication template override.",
    )
    assembly_default_delegation_document_mail_template_id = fields.Many2one(
        "mail.template",
        string="Default delegation document mail template",
        domain="[('model', '=', 'assembly.assembly')]",
        help="Used when an assembly has no delegation document template override.",
    )
    assembly_default_delegation_footer_mail_template_id = fields.Many2one(
        "mail.template",
        string="Default delegation footer mail template",
        domain="[('model', '=', 'assembly.assembly')]",
        help="Used when an assembly has no delegation footer template override.",
    )
    assembly_default_ballot_intro_mail_template_id = fields.Many2one(
        "mail.template",
        string="Default ballot introduction mail template",
        domain="[('model', '=', 'assembly.assembly')]",
        help="Used when an assembly has no ballot introduction template override.",
    )
    assembly_default_ballot_nominative_intro_mail_template_id = fields.Many2one(
        "mail.template",
        string="Default nominative ballot introduction mail template",
        domain="[('model', '=', 'assembly.assembly')]",
        help="Used when an assembly has no nominative ballot introduction override.",
    )
    assembly_af_publication_fallback_qweb_id = fields.Many2one(
        "ir.ui.view",
        string="Publication QWeb fallback",
        domain="[('type', '=', 'qweb')]",
        help="Rendered when publication mail templates and convocation HTML are empty.",
    )
    assembly_af_delegation_document_fallback_qweb_id = fields.Many2one(
        "ir.ui.view",
        string="Delegation document QWeb fallback",
        domain="[('type', '=', 'qweb')]",
    )
    assembly_af_delegation_footer_fallback_qweb_id = fields.Many2one(
        "ir.ui.view",
        string="Delegation footer QWeb fallback",
        domain="[('type', '=', 'qweb')]",
    )
    assembly_af_ballot_intro_fallback_qweb_id = fields.Many2one(
        "ir.ui.view",
        string="Ballot introduction QWeb fallback",
        domain="[('type', '=', 'qweb')]",
    )
    assembly_af_ballot_nominative_intro_fallback_qweb_id = fields.Many2one(
        "ir.ui.view",
        string="Nominative ballot introduction QWeb fallback",
        domain="[('type', '=', 'qweb')]",
    )
    assembly_attendance_landing_qweb_id = fields.Many2one(
        "ir.ui.view",
        string="Attendance deep-link landing page (QWeb)",
        domain="[('type', '=', 'qweb')]",
        help="HTML shown for manager attendance deep links when not using direct=1.",
    )
    assembly_attendance_error_qweb_id = fields.Many2one(
        "ir.ui.view",
        string="Attendance deep-link error page (QWeb)",
        domain="[('type', '=', 'qweb')]",
        help="HTML error page for attendance deep links (invalid access, wrong state, etc.).",
    )

    def _assembly_ensure_default_template_configuration(self):
        for company in self:
            updates = {}
            for field_name, xmlid in _ASSEMBLY_COMPANY_DEFAULT_CONFIG_REFS:
                if getattr(company, field_name):
                    continue
                rec = company.env.ref(xmlid, raise_if_not_found=False)
                if rec:
                    updates[field_name] = rec.id
            if updates:
                company.write(updates)

    def _assembly_sequence_create_values_from_template(self, template):
        self.ensure_one()
        return {
            "name": "%s — %s" % (template.name, self.name),
            "code": template.code,
            "implementation": template.implementation,
            "prefix": template.prefix,
            "suffix": template.suffix,
            "padding": template.padding,
            "number_increment": template.number_increment,
            "number_next": 1,
            "company_id": self.id,
        }

    def _assembly_ensure_numbering_sequence(self):
        ir_sequence = self.env["ir.sequence"].sudo()
        template = self.env.ref(
            "base_assembly.seq_assembly_assembly",
            raise_if_not_found=False,
        )
        for company in self:
            if company.assembly_sequence_id:
                continue
            existing = ir_sequence.search(
                [
                    ("code", "=", "assembly.assembly"),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            )
            if existing:
                company.assembly_sequence_id = existing
                continue
            if template:
                vals = company._assembly_sequence_create_values_from_template(template)
            else:
                vals = {
                    "name": "Assembly reference — %s" % company.name,
                    "code": "assembly.assembly",
                    "prefix": "ASM/%(year)s/",
                    "padding": 4,
                    "number_next": 1,
                    "number_increment": 1,
                    "company_id": company.id,
                }
            seq = ir_sequence.create(vals)
            company.assembly_sequence_id = seq

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._assembly_ensure_numbering_sequence()
        companies._assembly_ensure_default_template_configuration()
        return companies
