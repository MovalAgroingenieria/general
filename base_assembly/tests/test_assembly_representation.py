# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyRepresentation(AssemblyTestMixin, TransactionCase):
    def _assembly_with_three_convocable(self):
        partners = self._create_partners(self.env, 3, prefix="Rep")
        domain = "[('id', 'in', %s)]" % partners.ids
        assembly, _ = self._create_assembly_with_agenda(partner_domain=domain)
        return assembly, partners

    def test_representation_notes_field(self):
        """AF v2.0 optional notes on representation."""
        partners = self._create_partners(self.env, 2, prefix="RepNotes")
        domain = "[('id', 'in', %s)]" % partners.ids
        assembly, _agenda = self._create_assembly_with_agenda(
            name="Rep notes asm",
            partner_domain=domain,
        )
        rec = self.env["assembly.representation"].create(
            {
                "assembly_id": assembly.id,
                "owner_partner_id": partners[0].id,
                "agent_partner_id": partners[1].id,
                "notes": "Optional AF v2 note text",
            }
        )
        self.assertEqual(rec.notes, "Optional AF v2 note text")

    def test_representation_create_ok_and_linked_on_assembly(self):
        assembly, partners = self._assembly_with_three_convocable()
        rec = self.env["assembly.representation"].create(
            {
                "assembly_id": assembly.id,
                "owner_partner_id": partners[0].id,
                "agent_partner_id": partners[1].id,
            }
        )
        self.assertEqual(rec.assembly_id, assembly)
        self.assertTrue(rec.active)
        self.assertEqual(assembly.representation_ids, rec)

    def test_representation_does_not_change_attendee_vote_totals(self):
        """Legal representation rows do not trigger vote recomputation (separate from delegation)."""
        assembly, partners = self._assembly_with_three_convocable()
        self.assertTrue(assembly.vote_type_ids)
        vt = assembly.vote_type_ids[0]
        assembly.action_generate_attendees()
        att = assembly.attendee_ids.filtered(lambda a: a.partner_id == partners[0])
        self.assertTrue(att)
        att = att[0]
        self._confirm_attendees(att, vote_type=vt, votes_each=2)
        before = att.total_votes
        self.env["assembly.representation"].create(
            {
                "assembly_id": assembly.id,
                "owner_partner_id": partners[0].id,
                "agent_partner_id": partners[1].id,
            }
        )
        att.invalidate_recordset()
        self.assertEqual(att.total_votes, before)

    def test_representation_does_not_count_owner_toward_quorum(self):
        """Quorum presence uses attendees + vote delegations only, not legal representation."""
        assembly, partners = self._assembly_with_three_convocable()
        assembly.action_generate_attendees()
        agent_partner = partners[1]
        owner_partner = partners[0]
        att_agent = assembly.attendee_ids.filtered(
            lambda a: a.partner_id == agent_partner
        )
        self.assertTrue(att_agent)
        att_agent.action_confirm()
        self.env["assembly.representation"].create(
            {
                "assembly_id": assembly.id,
                "owner_partner_id": owner_partner.id,
                "agent_partner_id": agent_partner.id,
            }
        )
        assembly.invalidate_recordset()
        present = assembly._get_present_partner_ids()
        self.assertEqual(present, frozenset([agent_partner.id]))
        self.assertNotIn(owner_partner.id, present)

    def test_same_owner_different_assemblies_allowed(self):
        """One represented member may appear once per assembly, not globally."""
        partners = self._create_partners(self.env, 3, prefix="Rep2")
        domain = "[('id', 'in', %s)]" % partners.ids
        asm1, _ = self._create_assembly_with_agenda(
            name="Asm R1", partner_domain=domain
        )
        asm2, _ = self._create_assembly_with_agenda(
            name="Asm R2", partner_domain=domain
        )
        Representation = self.env["assembly.representation"]
        r1 = Representation.create(
            {
                "assembly_id": asm1.id,
                "owner_partner_id": partners[0].id,
                "agent_partner_id": partners[1].id,
            }
        )
        r2 = Representation.create(
            {
                "assembly_id": asm2.id,
                "owner_partner_id": partners[0].id,
                "agent_partner_id": partners[2].id,
            }
        )
        self.assertEqual(r1.owner_partner_id, r2.owner_partner_id)
        self.assertNotEqual(r1.assembly_id, r2.assembly_id)

    def test_representation_in_report_html(self):
        assembly, partners = self._assembly_with_three_convocable()
        self.env["assembly.representation"].create(
            {
                "assembly_id": assembly.id,
                "owner_partner_id": partners[0].id,
                "agent_partner_id": partners[1].id,
            }
        )
        report = self.env.ref(
            "base_assembly.assembly_assembly_action_report_representation"
        )
        html, _ = report._render_qweb_html(report.id, assembly.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertIn(partners[0].name, body)
        self.assertIn(partners[1].name, body)

    def test_representation_in_delegation_vote_report_html(self):
        """Delegation PDF includes ``report_assembly_representation_table_block`` when lines exist."""
        assembly, partners = self._assembly_with_three_convocable()
        self.env["assembly.representation"].create(
            {
                "assembly_id": assembly.id,
                "owner_partner_id": partners[0].id,
                "agent_partner_id": partners[1].id,
            }
        )
        report = self.env.ref(
            "base_assembly.assembly_assembly_action_report_delegationvote"
        )
        html, _ = report._render_qweb_html(report.id, assembly.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertIn("Representations (registered)", body)
        self.assertIn(partners[0].name, body)
        self.assertIn(partners[1].name, body)

    def test_representation_in_individual_call_report_html(self):
        assembly, partners = self._assembly_with_three_convocable()
        assembly.action_generate_attendees()
        self.env["assembly.representation"].create(
            {
                "assembly_id": assembly.id,
                "owner_partner_id": partners[0].id,
                "agent_partner_id": partners[1].id,
            }
        )
        attendee = assembly.attendee_ids[0]
        report = self.env.ref(
            "base_assembly.assembly_attendee_action_report_individual_call"
        )
        html, _ = report._render_qweb_html(report.id, attendee.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertIn("Representations (registered)", body)
        self.assertIn(partners[0].name, body)

    def test_representation_in_attendance_all_report_html(self):
        assembly, partners = self._assembly_with_three_convocable()
        self.env["assembly.representation"].create(
            {
                "assembly_id": assembly.id,
                "owner_partner_id": partners[0].id,
                "agent_partner_id": partners[1].id,
            }
        )
        report = self.env.ref(
            "base_assembly.assembly_assembly_action_report_attendance"
        )
        html, _ = report._render_qweb_html(report.id, assembly.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertIn("(registered)", body)
        self.assertIn(partners[0].name, body)
        self.assertIn(partners[1].name, body)

    def test_representation_in_attendance_present_report_html(self):
        assembly, partners = self._assembly_with_three_convocable()
        assembly.action_generate_attendees()
        for att in assembly.attendee_ids:
            att.action_confirm()
        self.env["assembly.representation"].create(
            {
                "assembly_id": assembly.id,
                "owner_partner_id": partners[0].id,
                "agent_partner_id": partners[1].id,
            }
        )
        report = self.env.ref(
            "base_assembly.assembly_assembly_action_report_attendance_with_signature"
        )
        html, _ = report._render_qweb_html(report.id, assembly.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertIn("(registered)", body)
        self.assertIn(partners[0].name, body)
        self.assertIn(partners[1].name, body)

    def test_closed_blocks_new_representation(self):
        assembly, partners = self._assembly_with_three_convocable()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        assembly.agenda_ids.action_skip()
        assembly.action_close()
        with self.assertRaises(UserError):
            self.env["assembly.representation"].create(
                {
                    "assembly_id": assembly.id,
                    "owner_partner_id": partners[0].id,
                    "agent_partner_id": partners[1].id,
                }
            )
