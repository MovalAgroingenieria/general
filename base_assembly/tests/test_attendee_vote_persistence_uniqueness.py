# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Uniqueness (attendee, vote type): repeated recompute and SQL constraint."""

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAttendeeVotePersistenceUniqueness(AssemblyTestMixin, TransactionCase):
    """Guarantees: one row per pair; stable totals; duplicates rejected."""

    def test_repeated_recompute_single_row_and_stable_totals(self):
        """(1)(2)(3) Many recomputes: single row and stable totals."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vt, 11)
        att.action_confirm()
        Av = self.env["assembly.attendee.vote"]
        for _ in range(15):
            att.recompute_attendee_vote_lines()
        self.assertEqual(
            Av.search_count(
                [
                    ("attendee_id", "=", att.id),
                    ("vote_type_id", "=", vt.id),
                ]
            ),
            1,
        )
        line = Av.search(
            [("attendee_id", "=", att.id), ("vote_type_id", "=", vt.id)], limit=1
        )
        self.assertEqual(line.own_votes, 11.0)
        self.assertEqual(line.attendee_vote_total, 11.0)

    def test_repeated_recompute_two_vote_types_one_row_each(self):
        """(2) Two types on the assembly → exactly two rows per attendee."""
        env = self.env
        vt1 = self._create_vote_type(env, name="Persist VT1")
        vt2 = self._create_vote_type(env, name="Persist VT2")
        atype = self._create_assembly_type(env, name="Persist type", vote_type=vt1)
        atype.write({"vote_type_ids": [(4, vt2.id)]})
        partners = self._create_partners(env, 2)
        assembly, _ = self._create_assembly_with_agenda(
            assembly_type=atype,
            partner_domain="[('id', 'in', %s)]" % partners.ids,
        )
        assembly.vote_type_ids = [(6, 0, [vt1.id, vt2.id])]
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vt1, 3)
        self._give_partner_votes(att.partner_id, vt2, 5)
        att.action_confirm()
        Av = env["assembly.attendee.vote"]
        for _ in range(10):
            att.recompute_attendee_vote_lines()
        self.assertEqual(Av.search_count([("attendee_id", "=", att.id)]), 2)
        l1 = Av.search(
            [("attendee_id", "=", att.id), ("vote_type_id", "=", vt1.id)], limit=1
        )
        l2 = Av.search(
            [("attendee_id", "=", att.id), ("vote_type_id", "=", vt2.id)], limit=1
        )
        self.assertEqual(l1.attendee_vote_total, 3.0)
        self.assertEqual(l2.attendee_vote_total, 5.0)

    def test_regression_recompute_after_delegation_still_one_row_each_endpoint(self):
        """Regression: delegation + multiple recomputes; one row per attendee/type."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        a, b = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(a.partner_id, vt, 8)
        self._give_partner_votes(b.partner_id, vt, 2)
        (a | b).action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(6, 0, vt.ids)],
                "delegation_state": "confirmed",
            }
        )
        Av = self.env["assembly.attendee.vote"]
        for _ in range(8):
            assembly.attendee_ids.recompute_attendee_vote_lines()
        self.assertEqual(
            Av.search_count(
                [
                    ("attendee_id", "in", (a | b).ids),
                    ("vote_type_id", "=", vt.id),
                ]
            ),
            2,
        )
        la = Av.search(
            [("attendee_id", "=", a.id), ("vote_type_id", "=", vt.id)], limit=1
        )
        lb = Av.search(
            [("attendee_id", "=", b.id), ("vote_type_id", "=", vt.id)], limit=1
        )
        self.assertEqual(la.attendee_vote_total, 0.0)
        self.assertEqual(lb.attendee_vote_total, 10.0)

    def test_duplicate_manual_create_same_pair_rejected(self):
        """(4) Second ``create`` for same (attendee, type) fails (SQL unique)."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vt, 1)
        att.action_confirm()
        att.recompute_attendee_vote_lines()
        Av = self.env["assembly.attendee.vote"]
        first = Av.search(
            [("attendee_id", "=", att.id), ("vote_type_id", "=", vt.id)], limit=1
        )
        self.assertTrue(first)
        with self.assertRaises(Exception):
            Av.create(
                {
                    "attendee_id": att.id,
                    "vote_type_id": vt.id,
                    "own_votes": 99.0,
                }
            )

    def test_repeated_recompute_preserves_same_database_row_id(self):
        """Same physical row updated (write), no new rows from recompute."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vt, 7)
        att.action_confirm()
        att.recompute_attendee_vote_lines()
        Av = self.env["assembly.attendee.vote"]
        line = Av.search(
            [("attendee_id", "=", att.id), ("vote_type_id", "=", vt.id)], limit=1
        )
        self.assertTrue(line)
        stable_id = line.id
        for _ in range(12):
            att.recompute_attendee_vote_lines()
        line_after = Av.search(
            [("attendee_id", "=", att.id), ("vote_type_id", "=", vt.id)], limit=1
        )
        self.assertEqual(line_after.id, stable_id)
        self.assertEqual(line_after.own_votes, 7.0)

    def test_collapse_duplicate_vote_lines_singleton_noop(self):
        """Collapse API: single record returned unchanged."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vt, 2)
        att.action_confirm()
        att.recompute_attendee_vote_lines()
        line = self.env["assembly.attendee.vote"].search(
            [("attendee_id", "=", att.id), ("vote_type_id", "=", vt.id)], limit=1
        )
        Attendee = self.env["assembly.attendee"]
        collapsed = Attendee._collapse_duplicate_attendee_vote_lines(line)
        self.assertEqual(collapsed, line)
        self.assertEqual(
            self.env["assembly.attendee.vote"].search_count(
                [("attendee_id", "=", att.id), ("vote_type_id", "=", vt.id)]
            ),
            1,
        )
