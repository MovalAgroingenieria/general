# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models

_ASSEMBLY_COMPANY_DEFAULT_CONFIG_REFS = (
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

    assembly_default_use_qr = fields.Boolean(
        string="Default tracked attendance links & QR",
        default=True,
        help="Default Include QR / tracked links for new company assemblies.",
    )
    assembly_allow_edit_closed_assembly = fields.Boolean(
        string="Allow editing closed assemblies",
        default=False,
        help="If set, assemblies in closed state can still be edited (per company).",
    )
    assembly_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Assembly reference sequence",
        domain="[('code', '=', 'assembly.assembly'), '|', "
        "('company_id', '=', False), ('company_id', '=', id)]",
        help="Sequence used to generate assembly reference codes. "
        "If empty, any sequence with code “assembly.assembly” is used.",
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
        help="HTML error page for attendance deep links (invalid access, "
        "wrong state, etc.).",
    )

    def _assembly_ensure_default_template_configuration(self):
        for record in self:
            updates = {}
            for field_name, xmlid in _ASSEMBLY_COMPANY_DEFAULT_CONFIG_REFS:
                if getattr(record, field_name):
                    continue
                rec = record.env.ref(xmlid, raise_if_not_found=False)
                if rec:
                    updates[field_name] = rec.id
            if updates:
                record.write(updates)

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
        for record in self:
            if record.assembly_sequence_id:
                continue
            existing = ir_sequence.search(
                [
                    ("code", "=", "assembly.assembly"),
                    ("company_id", "=", record.id),
                ],
                limit=1,
            )
            if existing:
                record.assembly_sequence_id = existing
                continue
            if template:
                vals = record._assembly_sequence_create_values_from_template(template)
            else:
                vals = {
                    "name": "Assembly reference — %s" % record.name,
                    "code": "assembly.assembly",
                    "prefix": "ASM/%(year)s/",
                    "padding": 4,
                    "number_next": 1,
                    "number_increment": 1,
                    "company_id": record.id,
                }
            seq = ir_sequence.create(vals)
            record.assembly_sequence_id = seq

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._assembly_ensure_numbering_sequence()
        companies._assembly_ensure_default_template_configuration()
        return companies

    @api.model
    def _assembly_sync_multicompany_ir_rule_domains(self):
        target = "[('company_id', 'in', company_ids)]"
        xmlids = (
            "base_assembly.assembly_type_rule_multicompany",
            "base_assembly.assembly_assembly_rule_multicompany",
            "base_assembly.assembly_agenda_rule_multicompany",
            "base_assembly.assembly_agenda_option_rule_multicompany",
            "base_assembly.assembly_attendee_rule_multicompany",
            "base_assembly.assembly_delegation_rule_multicompany",
            "base_assembly.assembly_representation_rule_multicompany",
            "base_assembly.assembly_voting_rule_multicompany",
            "base_assembly.assembly_voting_line_rule_multicompany",
            "base_assembly.assembly_voting_result_rule_multicompany",
            "base_assembly.assembly_attendee_vote_rule_multicompany",
        )
        for xid in xmlids:
            rule = self.env.ref(xid, raise_if_not_found=False)
            if not rule or rule.domain_force == target:
                continue
            rule.domain_force = target
