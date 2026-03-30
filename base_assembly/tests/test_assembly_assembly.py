# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyAssembly(  # pylint: disable=too-many-public-methods
    AssemblyTestMixin,
    TransactionCase,
):
    """Tests for assembly.assembly: creation, states, quorum, cancel, reopen."""

    # --- Creation (happy path) ---

    def test_assembly_create_assigns_code_from_sequence(self):
        assembly_type = self._create_assembly_type(
            self.env
        )  # pylint: disable=protected-access
        assembly = self.env["assembly.assembly"].create(
            {"name": "Asamblea test", "assembly_type_id": assembly_type.id}
        )
        self.assertTrue(assembly.code)
        self.assertNotEqual(assembly.code, "New")
        self.assertEqual(assembly.assembly_state, "draft")

    def test_assembly_create_with_type_copies_quorum_defaults(self):
        vote_type = self._create_vote_type(self.env)  # pylint: disable=protected-access
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "JG",
                "code": "JGCODE",
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "default_quorum_type": "percentage",
                "default_quorum_value": 25.0,
            }
        )
        assembly = self.env["assembly.assembly"].create(
            {"name": "Asamblea", "assembly_type_id": assembly_type.id}
        )
        self.assertEqual(assembly.quorum_type, "percentage")
        self.assertEqual(assembly.quorum_value, 25.0)

    def test_action_recompute_attendee_votes_recomputes_stored_lines(self):
        """AF §6: Assembly action rebuilds attendee vote snapshots from base_vote."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        for att in assembly.attendee_ids:
            self._give_partner_votes(att.partner_id, vote_type, 2.0)
            att.action_confirm()
        line = assembly.attendee_ids[0].attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertTrue(line)
        line.sudo().write({"own_votes": 0.0})
        assembly.action_recompute_attendee_votes()
        line.invalidate_recordset()
        self.assertEqual(line.own_votes, 2.0)

    def test_announce_with_agenda_changes_state_to_announced(self):
        assembly, _agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        self.assertEqual(assembly.assembly_state, "draft")
        assembly.action_announce()
        self.assertEqual(assembly.assembly_state, "announced")

    def test_announce_without_agenda_raises(self):
        assembly_type = self._create_assembly_type(
            self.env
        )  # pylint: disable=protected-access
        assembly = self.env["assembly.assembly"].create(
            {
<<<<<<< HEAD
                "name": "No agenda",
=======
                "name": "Sin agenda",
>>>>>>> origin/18.0
                "assembly_type_id": assembly_type.id,
                "partner_domain": "[]",
            }
        )
        with self.assertRaises(UserError) as ctx:
            assembly.action_announce()
        self.assertIn("agenda item must be added", str(ctx.exception))

    def test_announce_when_already_announced_is_noop(self):
        """Same-state transition is allowed; second announce does not raise."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_announce()
        assembly.action_announce()
        self.assertEqual(assembly.assembly_state, "announced")

        # --- States: open registration ---

    def test_open_registration_from_announced_changes_state_to_open(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_announce()
        assembly.action_open_registration()
        self.assertEqual(assembly.assembly_state, "open")

    def test_open_registration_from_draft_raises(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        with self.assertRaises(UserError) as ctx:
            assembly.action_open_registration()
        self.assertIn("draft → open", str(ctx.exception))

        # --- States: start session ---

    def test_start_session_from_open_sets_in_session_and_date_start(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_announce()
        assembly.action_open_registration()
        self.assertFalse(assembly.date_start)
        assembly.action_start_session()
        self.assertEqual(assembly.assembly_state, "in_session")
        self.assertTrue(assembly.date_start)

    def test_start_session_from_announced_raises(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_announce()
        with self.assertRaises(UserError) as ctx:
            assembly.action_start_session()
        self.assertIn("announced → in_session", str(ctx.exception))

        # --- Attendee generation (happy path and edge) ---

    def test_generate_attendees_creates_one_per_partner_in_domain(self):
        partners = self._create_partners(
            self.env, 3
        )  # pylint: disable=protected-access
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                partner_domain="[('id', 'in', %s)]" % partners.ids
            )
        )
        self.assertEqual(len(assembly.attendee_ids), 0)
        assembly.action_generate_attendees()
        self.assertEqual(len(assembly.attendee_ids), 3)
        self.assertEqual(
            set(assembly.attendee_ids.mapped("partner_id").ids), set(partners.ids)
        )

    def test_generate_attendees_idempotent_does_not_duplicate(self):
        partners = self._create_partners(
            self.env, 2
        )  # pylint: disable=protected-access
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                partner_domain="[('id', 'in', %s)]" % partners.ids
            )
        )
        assembly.action_generate_attendees()
        assembly.action_generate_attendees()
        self.assertEqual(len(assembly.attendee_ids), 2)

    def test_generate_attendees_with_empty_domain_does_not_fail(self):
        # Domain that returns no partners (search([]) would return all in DB)
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                partner_domain="[('id', '=', 0)]"
            )
        )
        assembly.action_generate_attendees()
        self.assertEqual(len(assembly.attendee_ids), 0)

    def test_generate_attendees_in_in_session_raises(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        with self.assertRaises(UserError) as ctx:
            assembly.action_generate_attendees()
        self.assertIn("Cannot generate attendees", str(ctx.exception))

        # --- Quorum ---

    def test_quorum_possible_equals_partners_in_domain(self):
        partners = self._create_partners(
            self.env, 5
        )  # pylint: disable=protected-access
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                partner_domain="[('id', 'in', %s)]" % partners.ids
            )
        )
        assembly.action_generate_attendees()
        self.assertEqual(assembly.total_possible_attendees, 5)

    def test_quorum_present_increases_when_attendee_confirmed(self):
        partners = self._create_partners(
            self.env, 3
        )  # pylint: disable=protected-access
        vote_type = self._create_vote_type(self.env)  # pylint: disable=protected-access
        assembly_type = self._create_assembly_type(self.env, vote_type=vote_type)
        # pylint: disable=protected-access
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                partner_domain="[('id', 'in', %s)]" % partners.ids,
                assembly_type=assembly_type,
            )
        )
        assembly.action_generate_attendees()
        assembly.action_announce()
        assembly.action_open_registration()
        self.assertEqual(assembly.total_present_attendees, 0)
        for att in assembly.attendee_ids[:2]:
            self._give_partner_votes(att.partner_id, vote_type, 1)
            # pylint: disable=protected-access
            att.action_confirm()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 2)

    def test_quorum_reached_when_percentage_above_threshold(self):
        partners = self._create_partners(  # noqa: F841
            self.env, 4
        )  # pylint: disable=protected-access
        vote_type = self._create_vote_type(self.env)  # pylint: disable=protected-access
        assembly_type = self._create_assembly_type(self.env, vote_type=vote_type)
        # pylint: disable=protected-access
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                partner_domain="[('id', 'in', %s)]" % partners.ids,
                assembly_type=assembly_type,
            )
        )
        assembly.quorum_value = 50.0
        assembly.action_generate_attendees()
        assembly.action_announce()
        assembly.action_open_registration()
        for att in assembly.attendee_ids[:2]:
            self._give_partner_votes(att.partner_id, vote_type, 1)
            # pylint: disable=protected-access
            att.action_confirm()
        assembly.invalidate_recordset()
        self.assertGreaterEqual(assembly.quorum_percentage, 50.0)
        self.assertTrue(assembly.quorum_reached)

    def test_quorum_invalid_partner_domain_does_not_crash(self):
        assembly, _ = self._create_assembly_with_agenda(partner_domain="[('invalid")
        # pylint: disable=protected-access
        assembly.action_generate_attendees()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 0)
        self.assertFalse(assembly.quorum_reached)

        # --- Close assembly (happy path and edge) ---

    def test_close_assembly_requires_no_open_votings_and_all_agenda_done(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_generate_attendees()
        assembly.action_start_session()
        agenda.action_skip()
        assembly.action_close()
        self.assertEqual(assembly.assembly_state, "closed")
        self.assertTrue(assembly.date_end)

    def test_close_assembly_with_open_voting_raises(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_generate_attendees()
        assembly.action_start_session()
        agenda.action_start_voting()
        with self.assertRaises(UserError) as ctx:
            assembly.action_close()
        self.assertIn("Close or cancel all open votings", str(ctx.exception))

    def test_close_assembly_with_pending_agenda_raises(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        with self.assertRaises(UserError) as ctx:
            assembly.action_close()
        self.assertIn("voted on or skipped", str(ctx.exception))

    def test_cancel_assembly_sets_cancelled_and_cancels_open_votings(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_generate_attendees()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = assembly.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.assertEqual(voting.voting_state, "open")
        assembly.action_cancel()
        self.assertEqual(assembly.assembly_state, "cancelled")
        voting.invalidate_recordset()
        self.assertEqual(voting.voting_state, "cancelled")

        # --- Reopen (happy path and edge) ---

    def test_reopen_removes_attendees_votings_and_resets_agenda(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_generate_attendees()
        self.assertEqual(len(assembly.attendee_ids), 3)
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(  # noqa: F841
            [("agenda_id", "=", agenda.id)], limit=1
        )
        assembly.action_cancel()
        assembly.action_reopen()
        self.assertEqual(assembly.assembly_state, "draft")
        self.assertEqual(len(assembly.attendee_ids), 0)
        self.assertFalse(voting.exists())
        self.assertEqual(agenda.agenda_state, "pending")

    def test_reopen_from_closed_raises(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_skip()
        assembly.action_close()
        with self.assertRaises(UserError) as ctx:
            assembly.action_reopen()
        self.assertIn("closed → draft", str(ctx.exception))
