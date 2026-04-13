# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import unittest

from markupsafe import Markup
from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError, UserError

from .common import AssemblyTestMixin


class TestAssemblyCommunicationMail(MailCommon, AssemblyTestMixin):
    def _assembly_with_emailed_attendees(self):
        assembly, _agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[:1]
        for att in assembly.attendee_ids:
            if vote_type:
                self._give_partner_votes(att.partner_id, vote_type, 1)
            att.partner_id.write({"email": "att%s@test.example.com" % att.id})
        return assembly

    def test_render_primary_body_returns_markup_for_html(self):
        assembly = self._assembly_with_emailed_attendees()
        svc = self.env["assembly.mail.communication"]
        body = svc._render_primary_body_html(assembly, "publication")
        self.assertIsInstance(body, Markup)

    def test_wizard_recipient_preview_count_all_mode(self):
        assembly = self._assembly_with_emailed_attendees()
        n = len(assembly.attendee_ids)
        wiz = self.env["assembly.communication.send.wizard"].create(
            {
                "assembly_id": assembly.id,
                "recipient_mode": "all",
                "recipient_audience": "all",
            }
        )
        self.assertEqual(wiz.email_recipient_count, n)
        self.assertIn(str(n), wiz.email_recipient_hint or "")

    def test_wizard_default_get_sets_attachment_defaults_by_message_kind(self):
        assembly = self._assembly_with_emailed_attendees()
        pub = (
            self.env["assembly.communication.send.wizard"]
            .with_context(
                default_primary_message_kind="publication",
            )
            .create({"assembly_id": assembly.id})
        )
        self.assertTrue(pub.attach_publication_pdf)
        self.assertFalse(pub.attach_nominative_ballot_pdf)
        self.assertFalse(pub.attach_delegation_pdf)
        ballot = (
            self.env["assembly.communication.send.wizard"]
            .with_context(
                default_primary_message_kind="ballot_intro",
            )
            .create({"assembly_id": assembly.id})
        )
        self.assertTrue(ballot.attach_nominative_ballot_pdf)
        self.assertFalse(ballot.attach_generic_ballot_pdf)
        deleg = (
            self.env["assembly.communication.send.wizard"]
            .with_context(
                default_primary_message_kind="delegation",
            )
            .create({"assembly_id": assembly.id})
        )
        self.assertTrue(deleg.attach_delegation_pdf)
        self.assertFalse(deleg.attach_publication_pdf)

    def test_send_to_partners_attaches_selected_pdfs(self):
        assembly = self._assembly_with_emailed_attendees()
        partner = assembly.attendee_ids[0].partner_id
        svc = self.env["assembly.mail.communication"]
        with self.mock_mail_gateway():
            sent, skipped, errors = svc.send_to_partners(
                assembly,
                partner,
                primary_kind="publication",
                attachment_options={
                    "attach_publication_pdf": True,
                    "attach_delegation_pdf": True,
                },
            )
        self.assertEqual(sent, 1)
        self.assertEqual(skipped, 0)
        self.assertFalse(errors)
        mail = self.env["mail.mail"].search(
            [
                ("model", "=", "assembly.assembly"),
                ("res_id", "=", assembly.id),
            ],
            limit=1,
        )
        self.assertTrue(mail)
        self.assertEqual(len(mail.attachment_ids), 2)

    def test_send_to_partners_rejects_assembly_outside_session_companies(self):
        assembly = self._assembly_with_emailed_attendees()
        c_asm = assembly.company_id
        self.assertTrue(c_asm)
        c_other = self.env["res.company"].create(
            {
                "name": "Mail MC other company",
                "currency_id": c_asm.currency_id.id,
            }
        )
        self.env.user.sudo().write({"company_ids": [(4, c_other.id)]})
        partner = assembly.attendee_ids[0].partner_id
        narrow = self.env(
            context={**self.env.context, "allowed_company_ids": [c_other.id]}
        )
        svc = narrow["assembly.mail.communication"]
        with self.assertRaises(UserError):
            svc.send_to_partners(
                assembly,
                partner,
                primary_kind="publication",
                attachment_options={},
            )

    def test_resolve_send_all_one_mail_per_partner(self):
        assembly = self._assembly_with_emailed_attendees()
        partners = assembly.attendee_ids.mapped("partner_id")
        self.assertGreaterEqual(len(partners), 1)
        svc = self.env["assembly.mail.communication"]
        with self.mock_mail_gateway():
            sent, skipped, errors = svc.send_to_partners(
                assembly,
                partners,
                primary_kind="publication",
                attachment_options={"attach_publication_pdf": False},
            )
        self.assertEqual(skipped, 0)
        self.assertFalse(errors)
        self.assertEqual(sent, len(partners))
        mails = self.env["mail.mail"].search(
            [
                ("model", "=", "assembly.assembly"),
                ("res_id", "=", assembly.id),
            ]
        )
        self.assertEqual(len(mails), len(partners))

    def test_wizard_send_all_posts_chatter_summary(self):
        assembly = self._assembly_with_emailed_attendees()
        wiz = self.env["assembly.communication.send.wizard"].create(
            {
                "assembly_id": assembly.id,
                "primary_message_kind": "publication",
                "recipient_mode": "all",
                "recipient_audience": "all",
                "attach_publication_pdf": False,
            }
        )
        with self.mock_mail_gateway():
            wiz.action_send_communication()
        bodies = assembly.message_ids.mapped("body")
        joined = " ".join(b or "" for b in bodies)
        self.assertIn("Outbound email batch", joined)

    def test_wizard_single_recipient_requires_email(self):
        assembly = self._assembly_with_emailed_attendees()
        if len(assembly.attendee_ids) < 2:
            self.skipTest("Need at least two attendees")
        partner_no = assembly.attendee_ids[0].partner_id
        partner_ok = assembly.attendee_ids[1].partner_id
        partner_no.write({"email": False})
        partner_ok.write({"email": "ok@test.example.com"})
        wiz = self.env["assembly.communication.send.wizard"].create(
            {
                "assembly_id": assembly.id,
                "primary_message_kind": "ballot_intro",
                "recipient_mode": "single",
                "partner_id": partner_no.id,
                "attach_nominative_ballot_pdf": False,
            }
        )
        with self.assertRaises(UserError):
            wiz.action_send_communication()
        wiz_ok = self.env["assembly.communication.send.wizard"].create(
            {
                "assembly_id": assembly.id,
                "primary_message_kind": "ballot_intro",
                "recipient_mode": "single",
                "partner_id": partner_ok.id,
                "attach_nominative_ballot_pdf": False,
            }
        )
        with self.mock_mail_gateway():
            wiz_ok.action_send_communication()

    def test_nominative_attachments_differ_per_partner(self):
        assembly = self._assembly_with_emailed_attendees()
        partners = assembly.attendee_ids.mapped("partner_id")[:2]
        if len(partners) < 2:
            self.skipTest("Need at least two attendees")
        svc = self.env["assembly.mail.communication"]
        opts = {"attach_nominative_ballot_pdf": True}
        ids_a = svc.build_attachment_ids_for_partner(assembly, partners[0], opts)
        ids_b = svc.build_attachment_ids_for_partner(assembly, partners[1], opts)
        self.assertTrue(ids_a and ids_b)
        self.assertNotEqual(ids_a, ids_b)

    def test_open_outbound_mails_action_domain(self):
        assembly = self._assembly_with_emailed_attendees()
        act = assembly.action_open_assembly_outbound_mails()
        self.assertEqual(act.get("res_model"), "mail.mail")
        self.assertEqual(
            act.get("domain"),
            [
                ("model", "=", "assembly.assembly"),
                ("res_id", "=", assembly.id),
            ],
        )

    def test_assembly_user_cannot_read_mail_mail(self):
        group_user = self.env.ref("base_assembly.assembly_group_user")
        base_user = self.env.ref("base.group_user")
        company = self.env.company
        try:
            asm_user = self.env["res.users"].create(
                {
                    "name": "Asm User Mail Test",
                    "login": "asm_user_mail_test",
                    "password": "asm_user_mail_test",
                    "company_id": company.id,
                    "company_ids": [(6, 0, [company.id])],
                    "groups_id": [(6, 0, [base_user.id, group_user.id])],
                }
            )
        except Exception as e:
            if "calendar_default_privacy" in str(e) or "not null" in str(e).lower():
                raise unittest.SkipTest(
                    "res.users.settings requires calendar (see security tests)"
                ) from e
            raise
        assembly = self._assembly_with_emailed_attendees()
        svc = self.env["assembly.mail.communication"]
        with self.mock_mail_gateway():
            svc.send_to_partners(
                assembly,
                assembly.attendee_ids.mapped("partner_id"),
                primary_kind="publication",
                attachment_options={},
            )
        env_u = self.env(user=asm_user)
        with self.assertRaises(AccessError):
            env_u["mail.mail"].search([("res_id", "=", assembly.id)])
