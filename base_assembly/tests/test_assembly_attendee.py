# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyAttendee(AssemblyTestMixin, TransactionCase):
    """Tests for assembly.attendee: confirm, absent, recompute_votes, constraint."""

    def test_confirm_sets_state_and_date_register(self):
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        self._give_partner_votes(
            att.partner_id, assembly.assembly_type_id.vote_type_ids[0], 1
        )
        self.assertEqual(att.attendee_state, "registered")
        self.assertFalse(att.date_register)
        att.action_confirm()
        self.assertEqual(att.attendee_state, "confirmed")
        self.assertTrue(att.date_register)

    def test_confirm_idempotent_when_already_confirmed(self):
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        self._give_partner_votes(
            att.partner_id, assembly.assembly_type_id.vote_type_ids[0], 1
        )
        att.action_confirm()
        date_first = att.date_register
        att.action_confirm()
        self.assertEqual(att.attendee_state, "confirmed")
        self.assertEqual(att.date_register, date_first)

    def test_mark_absent_sets_state_to_absent(self):
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        self._give_partner_votes(
            att.partner_id, assembly.assembly_type_id.vote_type_ids[0], 1
        )
        att.action_confirm()
        att.action_mark_absent()
        self.assertEqual(att.attendee_state, "absent")

    def test_recompute_votes_creates_attendee_vote_for_assembly_types(self):
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        self._give_partner_votes(att.partner_id, vote_type, 3)
        att.action_confirm()
        av = self.env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", att.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertTrue(av)
        self.assertEqual(av.own_votes, 3.0)
        self.assertEqual(av.attendee_vote_total, 3.0)

    def test_unique_assembly_partner_prevents_duplicate_attendee(self):
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        partner = assembly.attendee_ids[0].partner_id
        with self.assertRaises(Exception):
            self.env["assembly.attendee"].create(
                {"assembly_id": assembly.id, "partner_id": partner.id}
            )
