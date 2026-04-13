# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64

from markupsafe import Markup
from odoo import api, models
from odoo.exceptions import UserError


class AssemblyMailCommunication(models.AbstractModel):
    _name = "assembly.mail.communication"
    _description = "Assembly outbound communication helpers"

    @api.model
    def _partner_mail_lang(self, partner):
        if partner and partner.lang:
            return partner.lang
        return self.env.user.lang or "en_US"

    @api.model
    def _attendee_domain_for_audience(self, assembly, audience):
        domain = [("assembly_id", "=", assembly.id)]
        if audience == "confirmed":
            domain.append(("attendee_state", "=", "confirmed"))
        elif audience == "registered":
            domain.append(("attendee_state", "=", "registered"))
        return domain

    @api.model
    def _resolve_recipient_partners(
        self, assembly, *, recipient_mode, audience, single_partner
    ):
        Attendee = self.env["assembly.attendee"]
        if recipient_mode == "single":
            if not single_partner or not single_partner.exists():
                return self.env["res.partner"]
            if not Attendee.search_count(
                [
                    ("assembly_id", "=", assembly.id),
                    ("partner_id", "=", single_partner.id),
                ],
                limit=1,
            ):
                return self.env["res.partner"]
            return single_partner
        attendees = Attendee.search(
            self._attendee_domain_for_audience(assembly, audience)
        )
        partners = attendees.mapped("partner_id")
        return partners.filtered("email")

    @api.model
    def _render_primary_body_html(self, assembly, primary_kind, lang=None):
        asm = assembly.with_context(lang=lang) if lang else assembly
        if primary_kind == "publication":
            return Markup(asm.get_rendered_publication_text() or "")
        if primary_kind == "ballot_intro":
            return Markup(str(asm.get_rendered_ballot_intro_text() or ""))
        if primary_kind == "delegation":
            return Markup(str(asm.get_rendered_delegation() or ""))
        return Markup("")

    @api.model
    def _subject_for_kind(self, assembly, primary_kind, lang=None):
        if primary_kind == "publication":
            tmpl = (
                assembly.publication_mail_template_id
                or assembly._assembly_company_default_mail_template("publication")
                or assembly._assembly_mail_template_xmlid("publication")
            )
            return assembly._assembly_render_mail_subject(
                tmpl,
                self.env._("Assembly convocation: %s", assembly.name),
                lang=lang,
            )
        if primary_kind == "ballot_intro":
            tmpl = (
                assembly.ballot_intro_mail_template_id
                or assembly._assembly_company_default_mail_template("ballot_intro")
                or assembly._assembly_mail_template_xmlid("ballot_intro")
            )
            return assembly._assembly_render_mail_subject(
                tmpl,
                self.env._("Voting ballot: %s", assembly.name),
                lang=lang,
            )
        tmpl = (
            assembly.delegation_document_mail_template_id
            or assembly._assembly_company_default_mail_template("delegation_document")
            or assembly._assembly_mail_template_xmlid("delegation_document")
        )
        return assembly._assembly_render_mail_subject(
            tmpl,
            self.env._("Vote delegation: %s", assembly.name),
            lang=lang,
        )

    @api.model
    def _render_report_pdf(self, report_xmlid, res_ids, lang=None):
        report = self.env.ref(report_xmlid, raise_if_not_found=False)
        if not report or not res_ids:
            return None
        ir_report = self.env["ir.actions.report"]
        if lang:
            ir_report = ir_report.with_context(lang=lang)
        pdf_data, _ctype = ir_report._render_qweb_pdf(
            report.report_name,
            res_ids=res_ids,
        )
        return pdf_data

    @api.model
    def _create_pdf_attachment(self, filename, pdf_bytes):
        if not pdf_bytes:
            return self.env["ir.attachment"]
        return self.env["ir.attachment"].create(
            {
                "name": filename,
                "type": "binary",
                "datas": base64.b64encode(pdf_bytes),
                "mimetype": "application/pdf",
            }
        )

    @api.model
    def build_attachment_ids_for_partner(self, assembly, partner, options, lang=None):
        """Return ir.attachment ids for *options* (wizard-like dict) and *partner*."""
        att_ids = []
        if options.get("attach_publication_pdf"):
            pdf_bytes = self._render_report_pdf(
                "base_assembly.assembly_assembly_action_report_publication_document",
                [assembly.id],
                lang=lang,
            )
            if pdf_bytes:
                att = self._create_pdf_attachment(
                    "Publication-%s.pdf" % (assembly.code or str(assembly.id)),
                    pdf_bytes,
                )
                att_ids.append(att.id)
        if options.get("attach_generic_ballot_pdf"):
            attendees_all = self.env["assembly.attendee"].search(
                [("assembly_id", "=", assembly.id)],
                order="partner_id.name, id",
            )
            if attendees_all:
                pdf_bytes = self._render_report_pdf(
                    "base_assembly.assembly_attendee_action_report_voting_ballot_nominative",
                    attendees_all.ids,
                    lang=lang,
                )
                if pdf_bytes:
                    att = self._create_pdf_attachment(
                        "Member-ballots-merged-%s.pdf"
                        % (assembly.code or str(assembly.id)),
                        pdf_bytes,
                    )
                    att_ids.append(att.id)
        if options.get("attach_nominative_ballot_pdf"):
            attendee = self.env["assembly.attendee"].search(
                [
                    ("assembly_id", "=", assembly.id),
                    ("partner_id", "=", partner.id),
                ],
                limit=1,
            )
            if attendee:
                pdf_bytes = self._render_report_pdf(
                    "base_assembly.assembly_attendee_action_report_voting_ballot_nominative",
                    [attendee.id],
                    lang=lang,
                )
                if pdf_bytes:
                    att = self._create_pdf_attachment(
                        "Ballot-%s-%s.pdf"
                        % (
                            assembly.code or str(assembly.id),
                            partner.id,
                        ),
                        pdf_bytes,
                    )
                    att_ids.append(att.id)
        if options.get("attach_delegation_pdf"):
            pdf_bytes = self._render_report_pdf(
                "base_assembly.assembly_assembly_action_report_delegationvote",
                [assembly.id],
                lang=lang,
            )
            if pdf_bytes:
                att = self._create_pdf_attachment(
                    "Delegation-%s.pdf" % (assembly.code or str(assembly.id)),
                    pdf_bytes,
                )
                att_ids.append(att.id)
        return att_ids

    @api.model
    def send_to_partners(self, assembly, partners, *, primary_kind, attachment_options):
        """Send one email per partner; return ``(sent_count, skipped_no_email, errors)``."""
        assembly.ensure_one()
        session_cids = self.env.companies.ids
        ac = assembly.company_id
        if ac and session_cids and ac.id not in session_cids:
            raise UserError(
                self.env._(
                    "The assembly belongs to a company that is not in your current "
                    "session. Switch to that company or include it among your allowed "
                    "companies before sending mail."
                )
            )
        assembly._assembly_ensure_not_closed_for_related_changes()
        mail_composer_model = self.env["mail.compose.message"].with_context(
            assembly_use_rendered_mail_body=True,
            mail_create_nosubscribe=True,
        )
        sent = 0
        skipped = 0
        errors = []
        attach_opts = attachment_options or {}
        for partner in partners:
            if not partner.email:
                skipped += 1
                continue
            lang = self._partner_mail_lang(partner)
            body_base = self._render_primary_body_html(
                assembly, primary_kind, lang=lang
            )
            subject = self._subject_for_kind(assembly, primary_kind, lang=lang)
            att_ids = self.build_attachment_ids_for_partner(
                assembly, partner, attach_opts, lang=lang
            )
            try:
                composer = mail_composer_model.create(
                    {
                        "model": "assembly.assembly",
                        "res_ids": str([assembly.id]),
                        "composition_mode": "comment",
                        "partner_ids": [(6, 0, [partner.id])],
                        "subject": subject,
                        "body": body_base,
                        "attachment_ids": [(6, 0, att_ids)],
                    }
                )
                composer._action_send_mail()
                sent += 1
            except Exception as exc:  # pylint: disable=broad-exception-caught
                errors.append((partner.id, str(exc)))
                skipped += 1
        return sent, skipped, errors
