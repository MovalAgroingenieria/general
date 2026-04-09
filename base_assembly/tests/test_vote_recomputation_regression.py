# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Regression: stored ``assembly.attendee.vote`` rows after recompute (confirm, absent, delegation)."""

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestVoteRecomputationRegression(AssemblyTestMixin, TransactionCase):
    """Assertions always read persisted ``assembly.attendee.vote`` (search), not compute caches."""

    @staticmethod
    def _stored_vote_line(attendee, vote_type):
        return (
            attendee.env["assembly.attendee.vote"]
            .sudo()
            .search(
                [
                    ("attendee_id", "=", attendee.id),
                    ("vote_type_id", "=", vote_type.id),
                ],
                limit=1,
                order="id",
            )
        )

    def _assert_at_most_one_line_per_assembly_vote_type(self, attendees):
        Vote = self.env["assembly.attendee.vote"].sudo()
        for att in attendees:
            for vt in att.assembly_id.vote_type_ids:
                n = Vote.search_count(
                    [
                        ("attendee_id", "=", att.id),
                        ("vote_type_id", "=", vt.id),
                    ]
                )
                self.assertLessEqual(
                    n,
                    1,
                    "Multiple persisted rows for same attendee + vote type",
                )

    def _minimal_two_attendees(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        self.assertGreaterEqual(
            len(assembly.attendee_ids),
            2,
            "Fixture needs at least two attendees",
        )
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        return assembly, vote_type, assembly.attendee_ids[0], assembly.attendee_ids[1]

    def test_confirm_creates_persisted_own_vote_rows(self):
        """Protects: ``action_confirm`` runs vote recompute and persists one row per assembly vote type."""
        assembly, vote_type, att, _other = self._minimal_two_attendees()
        self._give_partner_votes(att.partner_id, vote_type, 6)
        line_before = self._stored_vote_line(att, vote_type)
        self.assertTrue(
            line_before,
            "Generate attendees must persist vote snapshot rows (from recompute at end)",
        )
        self.assertEqual(
            line_before.own_votes,
            0.0,
            "Partner votes after generate: refresh only on confirm/recompute/generate",
        )
        att.action_confirm()
        line = self._stored_vote_line(att, vote_type)
        self.assertTrue(line)
        self.assertEqual(line.own_votes, 6.0)
        self.assertEqual(line.delegated_out_votes, 0.0)
        self.assertEqual(line.delegated_in_votes, 0.0)
        self.assertEqual(line.attendee_vote_total, 6.0)
        self._assert_at_most_one_line_per_assembly_vote_type(att)

    def test_recompute_updates_persisted_row_after_partner_vote_change(self):
        """Protects: ``recompute_votes`` refreshes stored components from ``partner.vote`` (deterministic)."""
        assembly, vote_type, att, _other = self._minimal_two_attendees()
        self._give_partner_votes(att.partner_id, vote_type, 2)
        att.action_confirm()
        line = self._stored_vote_line(att, vote_type)
        self.assertEqual(line.own_votes, 2.0)
        self._give_partner_votes(att.partner_id, vote_type, 9)
        att.recompute_attendee_vote_lines()
        line.invalidate_recordset()
        line = self._stored_vote_line(att, vote_type)
        self.assertEqual(line.own_votes, 9.0)
        self.assertEqual(line.attendee_vote_total, 9.0)
        self._assert_at_most_one_line_per_assembly_vote_type(att)

    def test_mark_absent_persists_cleared_delegation_breakdown(self):
        """Protects: absent attendees do not apply delegation math; delegate lines lose inbound."""
        assembly, vote_type, delegator, delegate = self._minimal_two_attendees()
        self._give_partner_votes(delegator.partner_id, vote_type, 4)
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        delegator.action_confirm()
        delegate.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        d_line = self._stored_vote_line(delegator, vote_type)
        g_line = self._stored_vote_line(delegate, vote_type)
        self.assertEqual(d_line.delegated_out_votes, 4.0)
        self.assertEqual(g_line.delegated_in_votes, 4.0)
        delegator.action_mark_absent()
        d_line = self._stored_vote_line(delegator, vote_type)
        g_line = self._stored_vote_line(delegate, vote_type)
        self.assertEqual(d_line.own_votes, 4.0)
        self.assertEqual(d_line.delegated_out_votes, 0.0)
        self.assertEqual(d_line.delegated_in_votes, 0.0)
        self.assertEqual(d_line.attendee_vote_total, 4.0)
        self.assertEqual(g_line.delegated_in_votes, 0.0)
        self.assertEqual(g_line.attendee_vote_total, 1.0)
        self._assert_at_most_one_line_per_assembly_vote_type(delegator | delegate)

    def test_delegation_confirmed_persisted_in_out_totals(self):
        """Protects: confirmed delegation updates stored delegated_in/out on both endpoints."""
        assembly, vote_type, delegator, delegate = self._minimal_two_attendees()
        self._give_partner_votes(delegator.partner_id, vote_type, 5)
        self._give_partner_votes(delegate.partner_id, vote_type, 2)
        delegator.action_confirm()
        delegate.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        d_line_before = self._stored_vote_line(delegator, vote_type)
        self.assertEqual(d_line_before.delegated_out_votes, 0.0)
        d_line = self._stored_vote_line(delegator, vote_type)
        g_line = self._stored_vote_line(delegate, vote_type)
        self.assertEqual(d_line.delegated_out_votes, 5.0)
        self.assertEqual(g_line.delegated_in_votes, 5.0)
        self.assertEqual(g_line.attendee_vote_total, 7.0)
        self._assert_at_most_one_line_per_assembly_vote_type(delegator | delegate)

    def test_delegation_revoked_persisted_restores_own_only(self):
        """Protects: revoking delegation triggers recompute; stored lines drop in/out for that edge."""
        assembly, vote_type, delegator, delegate = self._minimal_two_attendees()
        self._give_partner_votes(delegator.partner_id, vote_type, 3)
        self._give_partner_votes(delegate.partner_id, vote_type, 2)
        delegator.action_confirm()
        delegate.action_confirm()
        del_rec = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        d_line = self._stored_vote_line(delegator, vote_type)
        g_line = self._stored_vote_line(delegate, vote_type)
        self.assertEqual(d_line.delegated_out_votes, 3.0)
        self.assertEqual(g_line.delegated_in_votes, 3.0)
        del_rec.unlink()
        d_line = self._stored_vote_line(delegator, vote_type)
        g_line = self._stored_vote_line(delegate, vote_type)
        self.assertEqual(d_line.delegated_out_votes, 0.0)
        self.assertEqual(g_line.delegated_in_votes, 0.0)
        self.assertEqual(d_line.attendee_vote_total, 3.0)
        self.assertEqual(g_line.attendee_vote_total, 2.0)
        self._assert_at_most_one_line_per_assembly_vote_type(delegator | delegate)

    def test_repeated_recompute_no_duplicate_vote_rows(self):
        """Protects: core recompute path keeps ≤1 persisted row per (attendee, vote type)."""
        assembly, vote_type, delegator, delegate = self._minimal_two_attendees()
        self._give_partner_votes(delegator.partner_id, vote_type, 1)
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        delegator.action_confirm()
        delegate.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        attendees = assembly.attendee_ids
        for _ in range(5):
            attendees.recompute_attendee_vote_lines()
        for att in attendees:
            self._assert_at_most_one_line_per_assembly_vote_type(att)

    def test_delegation_vote_transfer_only_after_delegate_confirmed(self):
        """Regression: confirm-path delegation pool is raw confirmed rows; effectiveness is one place.

        Partner/delegate rules apply only inside ``_get_effective_delegations`` (not
        by pre-filtering the pool). Until the delegate is confirmed, the delegator
        keeps full own votes.
        """
        assembly, vote_type, delegator, delegate = self._minimal_two_attendees()
        self._give_partner_votes(delegator.partner_id, vote_type, 5)
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        delegator.action_confirm()
        d_line = self._stored_vote_line(delegator, vote_type)
        self.assertEqual(d_line.delegated_out_votes, 0.0)
        delegate.action_confirm()
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()
        d_line = self._stored_vote_line(delegator, vote_type)
        g_line = self._stored_vote_line(delegate, vote_type)
        self.assertEqual(d_line.delegated_out_votes, 5.0)
        self.assertEqual(g_line.delegated_in_votes, 5.0)
