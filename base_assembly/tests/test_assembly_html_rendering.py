# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""AF v2.0: mail.template / QWeb rendering and PDF report sections (publication, agenda, ballots)."""

from markupsafe import Markup
from odoo.tests import TransactionCase
from odoo.tools import is_html_empty

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
        self.assertIn("o_assembly_delegation_intro", body)
        self.assertTrue(
            "o_assembly_delegation_footer" in body
            or "o_assembly_delegation_footer_fallback" in body,
            "Expected rendered footer block or standard fallback paragraph",
        )

    def test_voting_ballot_report_manual_yes_no_has_no_roll_call_checkboxes(self):
        """Manual yes/no items must not show the weighted roll-call checkbox row."""
        assembly, agenda = self._create_assembly_with_agenda(name="Ballot YN Asm")
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
            "base_assembly.assembly_assembly_action_report_voting_ballot"
        )
        html, _ = report._render_qweb_html(report.id, assembly.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertIn("Recorded — Yes:", body)
        self.assertNotIn("Yes ☐", body)

    def test_voting_ballot_report_lists_manual_multi_options(self):
        assembly, agenda = self._create_assembly_with_agenda(name="Ballot Multi Asm")
        vt = self._create_vote_type(self.env, name="VT Ballot", code="VTBALL01")
        assembly.write({"vote_type_ids": [(6, 0, vt.ids)]})
        agenda.write(
            {
                "agenda_vote_mode": "manual_multi",
                "requires_vote": False,
                "vote_type_id": False,
                "option_ids": [(0, 0, {"sequence": 10, "name": "OPTION_ALPHA_UNIQUE"})],
            }
        )
        report = self.env.ref(
            "base_assembly.assembly_assembly_action_report_voting_ballot"
        )
        html, _ = report._render_qweb_html(report.id, assembly.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertIn("OPTION_ALPHA_UNIQUE", body)
        self.assertIn("o_assembly_ballot_item", body)

    def test_attendance_all_report_includes_publication_render_block(self):
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
        self.assertIn("PUBLISH_AF_V2_BLOCK", body)
        self.assertIn("o_assembly_report_publication", body)

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
        self.assertIn("PRES_DEL_PUB", body)
        self.assertIn("Delegations received", body)
        self.assertIn("Attendees list (present only, with delegated votes)", body)

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
            "base_assembly.assembly_assembly_action_report_voting_ballot"
        )
        html, _ = report._render_qweb_html(report.id, assembly.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertIn("o_assembly_ballot_manual_counts", body)
        self.assertIn("Recorded", body)

    def test_mail_compose_publication_prefills_composer_with_rendered_html(self):
        """AF v2: convocation render is injected into ``mail.compose.message`` (real send path)."""
        assembly = self._create_assembly(name="Compose Pub Asm")
        assembly.write({"description": "<p>COMPOSE_PUB_UNIQUE</p>"})
        action = assembly.action_mail_compose_publication()
        self.assertEqual(action.get("res_model"), "mail.compose.message")
        ctx = dict(action.get("context") or {})
        self.assertTrue(ctx.get("assembly_use_rendered_mail_body"))
        composer = self.env["mail.compose.message"].with_context(ctx).create({})
        self.assertFalse(is_html_empty(composer.body))
        self.assertIn("Compose Pub Asm", str(composer.body))
        self.assertIn("COMPOSE_PUB_UNIQUE", str(composer.body))
        self.assertTrue((composer.subject or "").strip())

    def test_mail_compose_delegation_prefills_composer_with_rendered_html(self):
        """AF v2: bundled delegation render is injected into ``mail.compose.message``."""
        assembly = self._create_assembly(name="Compose Del Asm")
        action = assembly.action_mail_compose_delegation()
        ctx = dict(action.get("context") or {})
        self.assertTrue(ctx.get("assembly_use_rendered_mail_body"))
        composer = self.env["mail.compose.message"].with_context(ctx).create({})
        self.assertFalse(is_html_empty(composer.body))
        self.assertIn("Compose Del Asm", str(composer.body))
        self.assertIn("o_assembly_af_delegation_bundle", str(composer.body))
