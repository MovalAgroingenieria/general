# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""End-to-end test: full assembly flow from configuration to close and documents.

Covers: config → assembly creation → generate attendees → confirm → delegations
→ quorum → agenda (2 votings + 1 skip) → close → report generation.

See doc/E2E_TEST_DESIGN.md for scenario, variants and expected results.
"""

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyE2EFullFlow(AssemblyTestMixin, TransactionCase):
    """E2E: complete flow with concrete data (5 partners, 3 agenda items, delegations)."""

    def test_e2e_full_flow_in_person_with_delegation_and_documents(self):
        """
        Base scenario: in-person, with delegation David→Bruno.
        Steps 1–15 from E2E_TEST_DESIGN; final state checks and report generation.
        """
        env = self.env
        # --- 1. Configuration ---
        vote_type = self._create_vote_type(env, name="Cooperative vote", code="VCOOP")
        assembly_type = self._create_assembly_type(
            env, name="Ordinary General Meeting", vote_type=vote_type
        )
        assembly_type.write(
            {"default_quorum_type": "percentage", "default_quorum_value": 50.0}
        )
        # 5 partners: Ana(1), Bruno(2), Carla(1), David(3), Elena(1)
        partners = self._create_partners(env, count=5, prefix="Partner")
        votes_per_partner = [1, 2, 1, 3, 1]
        for partner, votes in zip(partners, votes_per_partner):
            self._give_partner_votes(partner, vote_type, votes)

        # --- 2. Assembly creation ---
        partner_domain = "[('id', 'in', %s)]" % partners.ids
        assembly = env["assembly.assembly"].create(
            {
                "name": "AGM 2025 - XYZ Cooperative",
                "assembly_type_id": assembly_type.id,
                "partner_domain": partner_domain,
                "quorum_type": "percentage",
                "quorum_value": 50.0,
            }
        )

        # --- 3. Agenda: 3 items (2 with vote, 1 without) ---
        agenda1 = env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Approval of previous minutes",
                "requires_vote": True,
                "vote_type_id": vote_type.id,
                "sequence": 10,
            }
        )
        env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Board information",
                "requires_vote": False,
                "sequence": 20,
            }
        )
        agenda3 = env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Approval of accounts",
                "requires_vote": True,
                "vote_type_id": vote_type.id,
                "sequence": 30,
            }
        )

        # --- 4–5. Announce and open registration ---
        assembly.action_announce()
        self.assertEqual(assembly.assembly_state, "announced")
        assembly.action_open_registration()
        self.assertEqual(assembly.assembly_state, "open")

        # --- 6. Generate convocable attendees ---
        assembly.action_generate_attendees()
        self.assertEqual(len(assembly.attendee_ids), 5)

        attendees = assembly.attendee_ids.sorted(key=lambda a: a.partner_id.name)
        ana, bruno, carla, david, elena = attendees

        # --- 7. Confirmation: Ana, Bruno, Carla ---
        ana.action_confirm()
        bruno.action_confirm()
        carla.action_confirm()
        self.assertEqual(assembly.count_present_attendees(), 3)
        assembly.invalidate_recordset()
        self.assertTrue(assembly.quorum_reached)

        # --- 8. Delegation David → Bruno; confirm delegation ---
        delegation = env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": david.partner_id.id,
                "delegate_partner_id": bruno.partner_id.id,
                "delegation_state": "draft",
            }
        )
        delegation.write({"delegation_state": "confirmed"})
        assembly.attendee_ids.recompute_votes()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.count_present_attendees(), 4)
        self.assertTrue(assembly.quorum_reached)

        # --- 9. Quorum ---
        self.assertEqual(assembly.total_possible_attendees, 5)
        self.assertEqual(assembly.total_present_attendees, 4)
        self.assertAlmostEqual(assembly.quorum_percentage, 80.0, places=1)

        # --- 10. Start session ---
        assembly.action_start_session()
        self.assertEqual(assembly.assembly_state, "in_session")
        self.assertTrue(assembly.date_start)

        # --- 11. Voting 1 (item 1) ---
        agenda1.action_start_voting()
        voting1 = env["assembly.voting"].search(
            [("agenda_id", "=", agenda1.id)], limit=1
        )
        self.assertEqual(voting1.voting_state, "open")
        env["assembly.voting.line"].create(
            [
                {
                    "voting_id": voting1.id,
                    "attendee_id": ana.id,
                    "vote_option": "yes",
                    "votes_applied": 1.0,
                },
                {
                    "voting_id": voting1.id,
                    "attendee_id": bruno.id,
                    "vote_option": "yes",
                    "votes_applied": 5.0,
                },
                {
                    "voting_id": voting1.id,
                    "attendee_id": carla.id,
                    "vote_option": "no",
                    "votes_applied": 1.0,
                },
            ]
        )
        voting1.invalidate_recordset()
        self.assertAlmostEqual(voting1.total_votes_cast, 7.0, places=2)
        self.assertAlmostEqual(voting1.total_votes_possible, 7.0, places=2)
        voting1.action_close()
        self.assertEqual(voting1.voting_state, "closed")
        self.assertEqual(agenda1.agenda_state, "voted")
        self.assertEqual(len(voting1.result_ids), 5)

        # --- 12. Punto 2: Skip ---
        agenda2 = env["assembly.agenda"].search(
            [("assembly_id", "=", assembly.id), ("name", "=", "Board information")],
            limit=1,
        )
        agenda2.action_skip()
        self.assertEqual(agenda2.agenda_state, "skipped")

        # --- 13. Voting 2 (item 3) ---
        agenda3.action_start_voting()
        voting2 = env["assembly.voting"].search(
            [("agenda_id", "=", agenda3.id)], limit=1
        )
        env["assembly.voting.line"].create(
            [
                {
                    "voting_id": voting2.id,
                    "attendee_id": ana.id,
                    "vote_option": "abstention",
                    "votes_applied": 1.0,
                },
                {
                    "voting_id": voting2.id,
                    "attendee_id": bruno.id,
                    "vote_option": "yes",
                    "votes_applied": 5.0,
                },
                {
                    "voting_id": voting2.id,
                    "attendee_id": carla.id,
                    "vote_option": "blank",
                    "votes_applied": 1.0,
                },
            ]
        )
        voting2.action_close()
        self.assertEqual(voting2.voting_state, "closed")
        self.assertEqual(agenda3.agenda_state, "voted")

        # --- 14. Close assembly ---
        assembly.action_close()
        self.assertEqual(assembly.assembly_state, "closed")
        self.assertTrue(assembly.date_end)

        # --- 15. Expected results ---
        self.assertEqual(len(assembly.attendee_ids), 5)
        self.assertEqual(assembly.count_present_attendees(), 4)
        self.assertEqual(len(assembly.delegation_ids), 1)
        self.assertEqual(assembly.delegation_ids.delegation_state, "confirmed")

        result_yes_1 = voting1.result_ids.filtered(lambda r: r.vote_option == "yes")
        self.assertEqual(len(result_yes_1), 1)
        self.assertAlmostEqual(result_yes_1.total_votes, 6.0, places=2)
        result_no_1 = voting1.result_ids.filtered(lambda r: r.vote_option == "no")
        self.assertAlmostEqual(result_no_1.total_votes, 1.0, places=2)

        total_result_votes = sum(voting1.result_ids.mapped("total_votes"))
        self.assertAlmostEqual(
            total_result_votes, voting1.total_votes_possible, places=2
        )

        # --- 16. Report generation (at least one without exception) ---
        report = env.ref("base_assembly.action_report_assembly_attendance")
        pdf, _ = report._render_qweb_pdf(report.id, assembly.ids, data={})
        self.assertIsInstance(pdf, bytes)
        self.assertGreater(len(pdf), 0)

        # Individual call for one attendee
        report_call = env.ref(
            "base_assembly.action_report_assembly_attendee_individual_call"
        )
        pdf_call, _ = report_call._render_qweb_pdf(report_call.id, ana.ids, data={})
        self.assertIsInstance(pdf_call, bytes)
        self.assertGreater(len(pdf_call), 0)
