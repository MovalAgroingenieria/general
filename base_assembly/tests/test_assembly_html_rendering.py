# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""AF v2.0: mail.template / QWeb rendering and PDF report sections (publication, agenda, ballots)."""

from markupsafe import Markup
from odoo.exceptions import UserError
from odoo.tests import TransactionCase
from odoo.tools import is_html_empty
from odoo.tools.safe_eval import safe_eval

from .common import AssemblyTestMixin


class TestAssemblyHtmlRendering(AssemblyTestMixin, TransactionCase):
    def test_get_rendered_publication_bare_assembly_fallback_not_empty(self):
        """Without ``description``, publication render must still yield non-empty HTML (title fallback)."""
        assembly = self._create_assembly(name="Bare Pub Asm")
        out = assembly.get_rendered_publication()
        self.assertIsInstance(out, Markup)
        s = str(out)
        self.assertTrue(s.strip())
        self.assertFalse(is_html_empty(s))
        self.assertIn("Bare Pub Asm", s)
        self.assertIn("o_assembly_publication_hint", s)

    def test_get_rendered_publication_with_description_has_no_duplicate_hint(self):
        assembly = self._create_assembly(name="Full Pub Asm")
        assembly.write({"description": "<p>BODY_WITH_HINT_CLASS</p>"})
        out = str(assembly.get_rendered_publication())
        self.assertIn("BODY_WITH_HINT_CLASS", out)
        self.assertEqual(out.count("o_assembly_publication_hint"), 0)

    def test_get_rendered_publication_returns_real_html_not_empty_with_body_data(self):
        """``get_rendered_publication()`` must yield non-empty HTML when ``description`` is set."""
        assembly = self._create_assembly(name="Pub Html Asm")
        assembly.write({"description": "<p>PUBLICATION_BODY_DATA_TOKEN</p>"})
        out = assembly.get_rendered_publication()
        self.assertIsInstance(out, Markup)
        s = str(out)
        self.assertFalse(
            is_html_empty(s), "publication must not be HTML-empty when data exists"
        )
        self.assertIn("<", s)
        self.assertIn("Pub Html Asm", s)
        self.assertIn("PUBLICATION_BODY_DATA_TOKEN", s)

    def test_get_rendered_delegation_returns_real_html_not_empty(self):
        """``get_rendered_delegation()`` bundles intro+footer; always non-empty Markup (defaults)."""
        assembly = self._create_assembly(name="Del Html Asm")
        out = assembly.get_rendered_delegation()
        self.assertIsInstance(out, Markup)
        s = str(out)
        self.assertFalse(is_html_empty(s))
        self.assertIn("<", s)
        self.assertIn("o_assembly_af_delegation_bundle", s)
        self.assertIn("Del Html Asm", s)

    def test_publication_uses_override_mail_template(self):
        assembly = self._create_assembly(name="Override Asm")
        tmpl = self.env["mail.template"].create(
            {
                "name": "Test override publication",
                "model_id": self.env["ir.model"]._get("assembly.assembly").id,
                "subject": "x",
                "body_html": (
                    '<div class="ovr"><p>UNIQUE_PUB_OVERRIDE_TOKEN</p>'
                    '<p t-out="object.name"/></div>'
                ),
            }
        )
        assembly.publication_mail_template_id = tmpl
        html = assembly.get_rendered_publication_text()
        self.assertIn("UNIQUE_PUB_OVERRIDE_TOKEN", str(html))
        self.assertIn("Override Asm", str(html))

    def test_delegation_document_and_footer_render_content(self):
        assembly = self._create_assembly(name="Del Render Asm")
        body = assembly.get_rendered_delegation_document_text()
        foot = assembly.get_rendered_delegation_footer_text()
        self.assertFalse(is_html_empty(str(body)))
        self.assertFalse(is_html_empty(str(foot)))
        self.assertIn("Del Render Asm", str(body))
        self.assertIn("delegator", str(foot).lower())
        combined = assembly.get_rendered_delegation()
        self.assertFalse(is_html_empty(str(combined)))
        self.assertIn("Del Render Asm", str(combined))
        self.assertIn("delegator", str(combined).lower())

    def test_ballot_intros_render_content(self):
        assembly = self._create_assembly(name="Ballot Asm")
        intro = assembly.get_rendered_ballot_intro_text()
        nom = assembly.get_rendered_ballot_nominative_intro_text()
        self.assertFalse(is_html_empty(str(intro)))
        self.assertFalse(is_html_empty(str(nom)))
        self.assertIn("Ballot Asm", str(intro))
        self.assertIn("Ballot Asm", str(nom))

    def test_rendering_always_returns_non_empty_html_all_entrypoints(self):
        """Production guard: no public render path may yield HTML-empty output (fallback chain)."""
        assembly = self._create_assembly(name="Prod render non-empty asm")
        fragments = [
            assembly.get_rendered_publication(),
            assembly.get_rendered_publication_text(),
            assembly.get_rendered_delegation_document_text(),
            assembly.get_rendered_delegation_footer_text(),
            assembly.get_rendered_delegation(),
            assembly.get_rendered_ballot_intro_text(),
            assembly.get_rendered_ballot_nominative_intro_text(),
        ]
        for idx, frag in enumerate(fragments):
            s = str(frag) if frag is not None else ""
            self.assertTrue(s.strip(), "fragment[%s] must not be whitespace-only" % idx)
            self.assertFalse(
                is_html_empty(s),
                "fragment[%s] must not be HTML-empty (odoo.tools.mail.is_html_empty)"
                % idx,
            )
        Wiz = self.env["assembly.document.preview.wizard"]
        for doc_type in (
            "publication",
            "delegation_body",
            "delegation_footer",
            "delegation_combined",
            "ballot_intro",
            "ballot_nominative",
        ):
            wiz = Wiz.create({"assembly_id": assembly.id, "document_type": doc_type})
            wiz.action_refresh_preview()
            prev = wiz.preview_html or ""
            self.assertTrue(prev.strip(), "wizard preview %s" % doc_type)
            self.assertFalse(is_html_empty(prev), "wizard preview %s" % doc_type)

    def test_preview_wizard_returns_non_empty_html(self):
        assembly = self._create_assembly(name="Wizard Asm")
        assembly.write({"description": "<p>Hello convocation</p>"})
        wiz = self.env["assembly.document.preview.wizard"].create(
            {
                "assembly_id": assembly.id,
                "document_type": "publication",
            }
        )
        action = wiz.action_refresh_preview()
        self.assertEqual(action.get("res_model"), "assembly.document.preview.wizard")
        self.assertFalse(is_html_empty(wiz.preview_html))
        self.assertIn("Wizard Asm", wiz.preview_html)
        self.assertIn("Hello convocation", wiz.preview_html)

    def test_preview_wizard_delegation_combined_non_empty(self):
        assembly = self._create_assembly(name="Wiz Del Asm")
        wiz = self.env["assembly.document.preview.wizard"].create(
            {
                "assembly_id": assembly.id,
                "document_type": "delegation_combined",
            }
        )
        wiz.action_refresh_preview()
        self.assertFalse(is_html_empty(wiz.preview_html))
        self.assertIn("Wiz Del Asm", wiz.preview_html)

    def test_af_qweb_fallback_views_are_loadable(self):
        for xmlid in (
            "base_assembly.assembly_af_publication_qweb",
            "base_assembly.assembly_af_delegation_document_qweb",
            "base_assembly.assembly_af_delegation_footer_qweb",
        ):
            view = self.env.ref(xmlid, raise_if_not_found=False)
            self.assertTrue(view, xmlid)
        assembly = self._create_assembly(name="Fallback Asm")
        html = assembly._render_assembly_af_qweb_fallback("publication")
        self.assertFalse(is_html_empty(str(html)))
        self.assertIn("Fallback Asm", str(html))

    def test_individual_call_report_includes_rendered_publication(self):
        assembly = self._create_assembly(name="Report Asm")
        assembly.write({"description": "<p>REP_BODY_TOKEN</p>"})
        partners = self._create_partners(self.env, 1, prefix="AttRep")
        assembly.write({"partner_domain": "[('id', 'in', %s)]" % partners.ids})
        assembly.action_generate_attendees()
        attendee = assembly.attendee_ids[0]
        report = self.env.ref(
            "base_assembly.assembly_attendee_action_report_individual_call"
        )
        html, _ = report._render_qweb_html(report.id, attendee.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertIn("REP_BODY_TOKEN", body)

    def test_individual_call_report_includes_agenda_item_html_description(self):
        assembly, _agenda = self._create_assembly_with_agenda(name="Agenda Html Asm")
        assembly.agenda_ids[0].write({"description": "<p>AGENDA_DESC_TOKEN_X7</p>"})
        partners = self._create_partners(self.env, 1, prefix="AgHtml")
        assembly.write({"partner_domain": "[('id', 'in', %s)]" % partners.ids})
        assembly.action_generate_attendees()
        attendee = assembly.attendee_ids[0]
        report = self.env.ref(
            "base_assembly.assembly_attendee_action_report_individual_call"
        )
        html, _ = report._render_qweb_html(report.id, attendee.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertIn("AGENDA_DESC_TOKEN_X7", body)

    def test_delegation_report_includes_rendered_intro_and_footer_blocks(self):
        assembly = self._create_assembly(name="Del Rep Asm")
        report = self.env.ref(
            "base_assembly.assembly_assembly_action_report_delegationvote"
        )
        html, _ = report._render_qweb_html(report.id, assembly.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertIn("o_assembly_delegation_register", body)
        self.assertTrue(
            "o_assembly_delegation_register_table" in body
            or "No delegation rows are registered" in body,
        )

    def test_delegation_report_print_name_uses_assembly_fields_only(self):
        assembly = self._create_assembly(name="Del Print Name Asm")
        report = self.env.ref(
            "base_assembly.assembly_assembly_action_report_delegationvote"
        )
        self.assertEqual(report.model, "assembly.assembly")
        printed = safe_eval(report.print_report_name, {"object": assembly})
        self.assertIn("Del Print Name Asm", printed)

    def test_delegation_report_pdf_render_succeeds(self):
        assembly = self._create_assembly(name="Del Pdf Asm")
        report = self.env.ref(
            "base_assembly.assembly_assembly_action_report_delegationvote"
        )
        pdf_data, _ctype = self.env["ir.actions.report"]._render_qweb_pdf(
            report.report_name, res_ids=assembly.ids
        )
        self.assertTrue(pdf_data)

    def test_voting_ballot_report_manual_yes_no_has_no_roll_call_checkboxes(self):
        """Manual yes/no items must not show the weighted roll-call checkbox row."""
        assembly, agenda = self._create_assembly_with_agenda(name="Ballot YN Asm")
        partners = self._create_partners(self.env, 1, prefix="BallYN")
        assembly.write({"partner_domain": "[('id', 'in', %s)]" % partners.ids})
        assembly.action_generate_attendees()
        agenda.write(
            {
                "agenda_vote_mode": "manual_yes_no",
                "requires_vote": False,
                "vote_type_id": False,
                "manual_yes": 0,
                "manual_no": 0,
                "manual_abstain": 0,
                "manual_count_blank": 0,
            }
        )
        report = self.env.ref(
            "base_assembly.assembly_attendee_action_report_voting_ballot_nominative"
        )
        att = assembly.attendee_ids[0]
        html, _ = report._render_qweb_html(report.id, att.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertIn("Recorded — Yes:", body)
        self.assertNotIn("Yes ☐", body)

    def test_voting_ballot_report_lists_manual_multi_options(self):
        assembly, agenda = self._create_assembly_with_agenda(name="Ballot Multi Asm")
        vt = self._create_vote_type(self.env, name="VT Ballot", code="VTBALL01")
        assembly.write({"vote_type_ids": [(6, 0, vt.ids)]})
        partners = self._create_partners(self.env, 1, prefix="BallMul")
        assembly.write({"partner_domain": "[('id', 'in', %s)]" % partners.ids})
        assembly.action_generate_attendees()
        agenda.write(
            {
                "agenda_vote_mode": "manual_multi",
                "requires_vote": False,
                "vote_type_id": False,
                "option_ids": [(0, 0, {"sequence": 10, "name": "OPTION_ALPHA_UNIQUE"})],
            }
        )
        report = self.env.ref(
            "base_assembly.assembly_attendee_action_report_voting_ballot_nominative"
        )
        att = assembly.attendee_ids[0]
        html, _ = report._render_qweb_html(report.id, att.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertIn("OPTION_ALPHA_UNIQUE", body)
        self.assertIn("o_assembly_ballot_item", body)
        self.assertIn("o_assembly_ballot_signatures", body)

    def test_attendance_all_report_excludes_convocation_body(self):
        assembly = self._create_assembly(name="Pub block asm")
        assembly.write({"description": "<p>PUBLISH_AF_V2_BLOCK</p>"})
        partners = self._create_partners(self.env, 1, prefix="PubAtt")
        assembly.write({"partner_domain": "[('id', 'in', %s)]" % partners.ids})
        assembly.action_generate_attendees()
        report = self.env.ref(
            "base_assembly.assembly_assembly_action_report_attendance"
        )
        html, _ = report._render_qweb_html(report.id, assembly.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertNotIn("PUBLISH_AF_V2_BLOCK", body)
        self.assertNotIn("o_assembly_report_publication", body)
        self.assertIn("o_assembly_report_operational_note", body)
        self.assertIn("Delegations received", body)
        self.assertIn("Delegations given", body)
        self.assertIn("o_assembly_report_roster_footer", body)

    def test_publication_pdf_report_renders_html_body_not_escaped(self):
        assembly = self._create_assembly(name="Esc Pub Asm")
        assembly.write(
            {"description": '<p class="o_asm_pub_esc_token">ESC_BODY_UNIQUE</p>'}
        )
        report = self.env.ref(
            "base_assembly.assembly_assembly_action_report_publication_document"
        )
        html, _ = report._render_qweb_html(report.id, assembly.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        pos = body.find("o_assembly_report_publication")
        self.assertGreater(pos, -1, "Expected publication wrapper in publication PDF")
        snippet = body[pos : pos + 1200]
        self.assertNotIn(
            "&lt;p",
            snippet,
            "Publication fragment must render as HTML, not escaped text",
        )
        self.assertIn("ESC_BODY_UNIQUE", snippet)
        self.assertIn("o_asm_pub_esc_token", snippet)

    def test_publication_pdf_includes_agenda_summary_compact(self):
        assembly, agenda = self._create_assembly_with_agenda(
            name="Pub Agenda Compact", requires_vote=False
        )
        agenda.write({"name": "UNIQUE_AGENDA_COMPACT_TITLE"})
        report = self.env.ref(
            "base_assembly.assembly_assembly_action_report_publication_document"
        )
        html, _ = report._render_qweb_html(report.id, assembly.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertIn("o_assembly_report_agenda_compact", body)
        self.assertIn("UNIQUE_AGENDA_COMPACT_TITLE", body)

    def test_call_register_report_is_distinct_template(self):
        assembly = self._create_assembly(name="Call Reg Asm")
        partners = self._create_partners(self.env, 1, prefix="CallReg")
        assembly.write({"partner_domain": "[('id', 'in', %s)]" % partners.ids})
        assembly.action_generate_attendees()
        assembly.attendee_ids.action_confirm()
        report = self.env.ref(
            "base_assembly.assembly_assembly_action_report_call_register"
        )
        self.assertEqual(
            report.report_name, "base_assembly.report_assembly_attendance_call_register"
        )
        html, _ = report._render_qweb_html(report.id, assembly.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertIn("o_assembly_report_call_register", body)
        self.assertIn("Call register", body)
        self.assertNotIn("o_assembly_report_operational_note", body)

    def test_voting_ballot_nominative_report_uses_nominative_intro_not_standard(self):
        assembly = self._create_assembly(name="Ballot Intro Split")
        model_asm = self.env["ir.model"]._get("assembly.assembly").id
        tmpl_std = self.env["mail.template"].create(
            {
                "name": "Std ballot intro test",
                "model_id": model_asm,
                "subject": "x",
                "body_html": "<p>BALLOT_INTRO_STD_UNIQUE_TOKEN</p>",
            }
        )
        tmpl_nom = self.env["mail.template"].create(
            {
                "name": "Nom ballot intro test",
                "model_id": model_asm,
                "subject": "x",
                "body_html": "<p>BALLOT_INTRO_NOM_UNIQUE_TOKEN</p>",
            }
        )
        assembly.write(
            {
                "ballot_intro_mail_template_id": tmpl_std.id,
                "ballot_nominative_intro_mail_template_id": tmpl_nom.id,
            }
        )
        partners = self._create_partners(self.env, 1, prefix="BallIntro")
        assembly.write({"partner_domain": "[('id', 'in', %s)]" % partners.ids})
        assembly.action_generate_attendees()
        vt = assembly.vote_type_ids[0]
        self._confirm_attendees(assembly.attendee_ids, vote_type=vt, votes_each=1)
        att = assembly.attendee_ids[0]
        rep_std = self.env.ref(
            "base_assembly.assembly_attendee_action_report_voting_ballot"
        )
        rep_nom = self.env.ref(
            "base_assembly.assembly_attendee_action_report_voting_ballot_nominative"
        )
        html_std, _ = rep_std._render_qweb_html(rep_std.id, att.ids, data={})
        body_std = html_std.decode() if isinstance(html_std, bytes) else html_std
        html_nom, _ = rep_nom._render_qweb_html(rep_nom.id, att.ids, data={})
        body_nom = html_nom.decode() if isinstance(html_nom, bytes) else html_nom
        self.assertIn("BALLOT_INTRO_STD_UNIQUE_TOKEN", body_std)
        self.assertNotIn("BALLOT_INTRO_NOM_UNIQUE_TOKEN", body_std)
        self.assertIn("BALLOT_INTRO_NOM_UNIQUE_TOKEN", body_nom)
        self.assertNotIn("BALLOT_INTRO_STD_UNIQUE_TOKEN", body_nom)

    def test_attendance_present_with_delegation_report_renders(self):
        assembly = self._create_assembly(name="PresDel Asm")
        assembly.write({"description": "<p>PRES_DEL_PUB</p>"})
        partners = self._create_partners(self.env, 2, prefix="PresDel")
        assembly.write({"partner_domain": "[('id', 'in', %s)]" % partners.ids})
        assembly.action_generate_attendees()
        vt = assembly.vote_type_ids[0]
        self._confirm_attendees(assembly.attendee_ids, vote_type=vt, votes_each=1)
        report = self.env.ref(
            "base_assembly.assembly_assembly_action_report_attendance_present_with_delegationvote"
        )
        html, _ = report._render_qweb_html(report.id, assembly.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertNotIn("PRES_DEL_PUB", body)
        self.assertIn("o_assembly_report_operational_note", body)
        self.assertIn("Delegations received", body)
        self.assertIn("Attendance sheet (present, with delegated votes)", body)

    def test_individual_call_report_includes_agenda_manual_and_final_summary(self):
        assembly, agenda = self._create_assembly_with_agenda(
            name="Indiv AF asm", requires_vote=False
        )
        partners = self._create_partners(self.env, 1, prefix="IndivP")
        assembly.write({"partner_domain": "[('id', 'in', %s)]" % partners.ids})
        assembly.action_generate_attendees()
        vt = assembly.vote_type_ids[0]
        self._confirm_attendees(assembly.attendee_ids, vote_type=vt, votes_each=1)
        agenda.write(
            {
                "agenda_vote_mode": "manual_yes_no",
                "requires_vote": False,
                "vote_type_id": False,
                "manual_yes": 1,
                "manual_no": 0,
                "manual_abstain": 0,
                "manual_count_blank": 0,
                "final_summary": "<p>FINAL_SUMMARY_AF_CALL</p>",
            }
        )
        attendee = assembly.attendee_ids[0]
        report = self.env.ref(
            "base_assembly.assembly_attendee_action_report_individual_call"
        )
        html, _ = report._render_qweb_html(report.id, attendee.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertIn("FINAL_SUMMARY_AF_CALL", body)
        self.assertIn("o_assembly_report_final_summary", body)
        self.assertIn("o_assembly_report_manual_yn", body)
        self.assertIn("Manual counts", body)

    def test_voting_ballot_report_shows_manual_yes_no_recorded_line(self):
        assembly, agenda = self._create_assembly_with_agenda(name="Ballot AF asm")
        vt = self._create_vote_type(self.env, name="VT Ballot AF", code="VTBAF01")
        assembly.write({"vote_type_ids": [(6, 0, vt.ids)]})
        assembly.action_generate_attendees()
        self._confirm_attendees(assembly.attendee_ids, vote_type=vt, votes_each=1)
        agenda.write(
            {
                "agenda_vote_mode": "manual_yes_no",
                "requires_vote": False,
                "vote_type_id": False,
                "manual_yes": 2,
                "manual_no": 1,
                "manual_abstain": 0,
                "manual_count_blank": 0,
            }
        )
        report = self.env.ref(
            "base_assembly.assembly_attendee_action_report_voting_ballot_nominative"
        )
        att = assembly.attendee_ids[0]
        html, _ = report._render_qweb_html(report.id, att.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertIn("o_assembly_ballot_manual_counts", body)
        self.assertIn("Recorded", body)

    def test_voting_ballot_per_attendee_shows_power_and_weighted_row(self):
        assembly, agenda = self._create_assembly_with_agenda(name="Ballot Att Id")
        partners = self._create_partners(self.env, 1, prefix="BallAtt")
        assembly.write({"partner_domain": "[('id', 'in', %s)]" % partners.ids})
        assembly.action_generate_attendees()
        vt = assembly.vote_type_ids[0]
        self._confirm_attendees(assembly.attendee_ids, vote_type=vt, votes_each=1)
        self.assertEqual(agenda.agenda_vote_mode, "weighted")
        report = self.env.ref(
            "base_assembly.assembly_attendee_action_report_voting_ballot_nominative"
        )
        att = assembly.attendee_ids[0]
        html, _ = report._render_qweb_html(report.id, att.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertIn("o_assembly_ballot_identity", body)
        self.assertIn("Attendee name", body)
        self.assertIn("Total voting power", body)
        self.assertIn("Yes ☐", body)
        self.assertIn("o_assembly_ballot_weighted_choices", body)

    def test_mail_compose_publication_opens_communication_wizard(self):
        assembly = self._create_assembly(name="Compose Pub Asm")
        assembly.write({"description": "<p>COMPOSE_PUB_UNIQUE</p>"})
        action = assembly.action_mail_compose_publication()
        self.assertEqual(action.get("res_model"), "assembly.communication.send.wizard")
        ctx = dict(action.get("context") or {})
        self.assertEqual(ctx.get("default_primary_message_kind"), "publication")
        svc = self.env["assembly.mail.communication"]
        body = svc._render_primary_body_html(assembly, "publication")
        self.assertFalse(is_html_empty(body))
        self.assertIn("Compose Pub Asm", str(body))
        self.assertIn("COMPOSE_PUB_UNIQUE", str(body))
        self.assertTrue((svc._subject_for_kind(assembly, "publication") or "").strip())

    def test_mail_compose_delegation_opens_wizard_and_renders_bundle(self):
        assembly = self._create_assembly(name="Compose Del Asm")
        action = assembly.action_mail_compose_delegation()
        self.assertEqual(action.get("res_model"), "assembly.communication.send.wizard")
        ctx = dict(action.get("context") or {})
        self.assertEqual(ctx.get("default_primary_message_kind"), "delegation")
        svc = self.env["assembly.mail.communication"]
        body = svc._render_primary_body_html(assembly, "delegation")
        self.assertFalse(is_html_empty(body))
        self.assertIn("Compose Del Asm", str(body))
        self.assertIn("o_assembly_af_delegation_bundle", str(body))

    def test_core_assembly_pdf_reports_render_without_error(self):
        assembly, _ag = self._create_assembly_with_agenda(name="Pdf smoke asm")
        partners = self._create_partners(self.env, 2, prefix="PdfSmoke")
        assembly.write({"partner_domain": "[('id', 'in', %s)]" % partners.ids})
        assembly.action_generate_attendees()
        vt = assembly.vote_type_ids[0]
        self._confirm_attendees(assembly.attendee_ids, vote_type=vt, votes_each=1)
        att = assembly.attendee_ids[0]
        self.env["assembly.representation"].create(
            {
                "assembly_id": assembly.id,
                "owner_partner_id": partners[0].id,
                "agent_partner_id": partners[1].id,
            }
        )
        rep_rec = self.env["assembly.representation"].search(
            [("assembly_id", "=", assembly.id)], limit=1
        )
        IrReport = self.env["ir.actions.report"]
        for xmlid in (
            "base_assembly.assembly_assembly_action_report_attendance",
            "base_assembly.assembly_assembly_action_report_attendance_with_signature",
            "base_assembly.assembly_assembly_action_report_attendance_with_delegationvote",
            "base_assembly.assembly_assembly_action_report_attendance_present_with_delegationvote",
            "base_assembly.assembly_assembly_action_report_publication_document",
            "base_assembly.assembly_assembly_action_report_delegationvote",
            "base_assembly.assembly_assembly_action_report_representation",
            "base_assembly.assembly_assembly_action_report_call_register",
        ):
            report = self.env.ref(xmlid)
            pdf_data, _fmt = IrReport._render_qweb_pdf(
                report.report_name, res_ids=assembly.ids
            )
            self.assertTrue(pdf_data, xmlid)
        ballot_nom_merge = self.env.ref(
            "base_assembly.assembly_attendee_action_report_voting_ballot_nominative"
        )
        pdf_data, _fmt = IrReport._render_qweb_pdf(
            ballot_nom_merge.report_name, res_ids=assembly.attendee_ids.ids
        )
        self.assertTrue(pdf_data, "merged member ballots PDF")
        ballot_tpl = self.env.ref(
            "base_assembly.assembly_attendee_action_report_voting_ballot"
        )
        pdf_data, _fmt = IrReport._render_qweb_pdf(
            ballot_tpl.report_name, res_ids=att.ids
        )
        self.assertTrue(pdf_data, "generic intro template ballot")
        indiv = self.env.ref(
            "base_assembly.assembly_attendee_action_report_individual_call"
        )
        pdf_data, _fmt = IrReport._render_qweb_pdf(indiv.report_name, res_ids=att.ids)
        self.assertTrue(pdf_data)
        indiv_v = self.env.ref(
            "base_assembly.assembly_attendee_action_report_individual_call_with_votes"
        )
        pdf_data, _fmt = IrReport._render_qweb_pdf(indiv_v.report_name, res_ids=att.ids)
        self.assertTrue(pdf_data)
        poa = self.env.ref(
            "base_assembly.assembly_representation_action_report_power_of_attorney"
        )
        pdf_data, _fmt = IrReport._render_qweb_pdf(poa.report_name, res_ids=rep_rec.ids)
        self.assertTrue(pdf_data)
        del_rec = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": partners[0].id,
                "delegate_partner_id": partners[1].id,
                "vote_type_ids": [(6, 0, vt.ids)],
            }
        )
        cert = self.env.ref(
            "base_assembly.assembly_delegation_action_report_vote_delegation_certificate"
        )
        pdf_data, _fmt = IrReport._render_qweb_pdf(
            cert.report_name, res_ids=del_rec.ids
        )
        self.assertTrue(pdf_data, "delegation certificate PDF")

    def test_ballot_print_wizard_only_present_default_excludes_unconfirmed(self):
        assembly, _ag = self._create_assembly_with_agenda(name="Ballot pres def asm")
        partners = self._create_partners(self.env, 1, prefix="BPrDef")
        assembly.write({"partner_domain": "[('id', 'in', %s)]" % partners.ids})
        assembly.action_generate_attendees()
        wiz = self.env["assembly.ballot.print.wizard"].create(
            {"assembly_id": assembly.id},
        )
        self.assertTrue(wiz.only_present)
        with self.assertRaises(UserError):
            wiz.with_context(discard_logo_check=True).action_print_ballots()

    def test_ballot_print_wizard_merged_and_zip(self):
        assembly, _ag = self._create_assembly_with_agenda(name="Ballot wiz asm")
        partners = self._create_partners(self.env, 2, prefix="BWiz")
        assembly.write({"partner_domain": "[('id', 'in', %s)]" % partners.ids})
        assembly.action_generate_attendees()
        wiz = self.env["assembly.ballot.print.wizard"].create(
            {
                "assembly_id": assembly.id,
                "only_present": False,
                "merge_single_pdf": True,
            }
        )
        act_merge = wiz.with_context(discard_logo_check=True).action_print_ballots()
        self.assertEqual(act_merge.get("type"), "ir.actions.report")
        nom_rep = self.env.ref(
            "base_assembly.assembly_attendee_action_report_voting_ballot_nominative"
        )
        self.assertEqual(act_merge.get("report_name"), nom_rep.report_name)
        wiz.merge_single_pdf = False
        act_zip = wiz.with_context(discard_logo_check=True).action_print_ballots()
        self.assertEqual(act_zip.get("type"), "ir.actions.act_url")
        self.assertIn("/web/content/", act_zip.get("url", ""))

    def test_ballot_print_wizard_optional_generic_intro_report(self):
        assembly, _ag = self._create_assembly_with_agenda(name="Ballot wiz generic asm")
        partners = self._create_partners(self.env, 1, prefix="BWizGen")
        assembly.write({"partner_domain": "[('id', 'in', %s)]" % partners.ids})
        assembly.action_generate_attendees()
        vt = assembly.vote_type_ids[0]
        self._confirm_attendees(assembly.attendee_ids, vote_type=vt, votes_each=1)
        wiz = self.env["assembly.ballot.print.wizard"].create(
            {
                "assembly_id": assembly.id,
                "only_present": True,
                "merge_single_pdf": True,
                "use_generic_intro_template": True,
            }
        )
        act = wiz.with_context(discard_logo_check=True).action_print_ballots()
        gen_rep = self.env.ref(
            "base_assembly.assembly_attendee_action_report_voting_ballot"
        )
        self.assertEqual(act.get("report_name"), gen_rep.report_name)

    def test_attendee_print_ballot_action_is_report(self):
        assembly, _ag = self._create_assembly_with_agenda(name="Att ballot act")
        partners = self._create_partners(self.env, 1, prefix="AttBalAct")
        assembly.write({"partner_domain": "[('id', 'in', %s)]" % partners.ids})
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        nom_rep = self.env.ref(
            "base_assembly.assembly_attendee_action_report_voting_ballot_nominative"
        )
        act = att.with_context(discard_logo_check=True).action_print_ballot()
        self.assertEqual(act.get("type"), "ir.actions.report")
        self.assertEqual(act.get("report_name"), nom_rep.report_name)
