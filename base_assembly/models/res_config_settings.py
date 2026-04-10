# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    assembly_default_use_qr = fields.Boolean(
        related="company_id.assembly_default_use_qr",
        readonly=False,
    )
    assembly_allow_edit_closed_assembly = fields.Boolean(
        related="company_id.assembly_allow_edit_closed_assembly",
        readonly=False,
    )
    assembly_sequence_id = fields.Many2one(
        related="company_id.assembly_sequence_id",
        readonly=False,
    )
    assembly_default_publication_mail_template_id = fields.Many2one(
        related="company_id.assembly_default_publication_mail_template_id",
        readonly=False,
    )
    assembly_default_delegation_document_mail_template_id = fields.Many2one(
        related="company_id.assembly_default_delegation_document_mail_template_id",
        readonly=False,
    )
    assembly_default_delegation_footer_mail_template_id = fields.Many2one(
        related="company_id.assembly_default_delegation_footer_mail_template_id",
        readonly=False,
    )
    assembly_default_ballot_intro_mail_template_id = fields.Many2one(
        related="company_id.assembly_default_ballot_intro_mail_template_id",
        readonly=False,
    )
    assembly_default_ballot_nominative_intro_mail_template_id = fields.Many2one(
        related="company_id.assembly_default_ballot_nominative_intro_mail_template_id",
        readonly=False,
    )
    assembly_af_publication_fallback_qweb_id = fields.Many2one(
        related="company_id.assembly_af_publication_fallback_qweb_id",
        readonly=False,
    )
    assembly_af_delegation_document_fallback_qweb_id = fields.Many2one(
        related="company_id.assembly_af_delegation_document_fallback_qweb_id",
        readonly=False,
    )
    assembly_af_delegation_footer_fallback_qweb_id = fields.Many2one(
        related="company_id.assembly_af_delegation_footer_fallback_qweb_id",
        readonly=False,
    )
    assembly_af_ballot_intro_fallback_qweb_id = fields.Many2one(
        related="company_id.assembly_af_ballot_intro_fallback_qweb_id",
        readonly=False,
    )
    assembly_af_ballot_nominative_intro_fallback_qweb_id = fields.Many2one(
        related="company_id.assembly_af_ballot_nominative_intro_fallback_qweb_id",
        readonly=False,
    )
    assembly_attendance_landing_qweb_id = fields.Many2one(
        related="company_id.assembly_attendance_landing_qweb_id",
        readonly=False,
    )
    assembly_attendance_error_qweb_id = fields.Many2one(
        related="company_id.assembly_attendance_error_qweb_id",
        readonly=False,
    )
