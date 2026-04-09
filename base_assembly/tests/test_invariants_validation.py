# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Production-grade tests for invariants validation.

Tests that all mathematical and business invariants are enforced:
- No negative votes
- No delegation to non-existing attendee
- No effective delegation without confirmed delegate
- Mathematical consistency (total = own + in - out)
- Vote conservation
"""

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase
from psycopg2 import errors as pg_errors

from .common import AssemblyTestMixin


class TestInvariantsValidation(AssemblyTestMixin, TransactionCase):
    """Test that all invariants are properly validated and enforced."""

    def test_no_negative_votes_constraint(self):
        """SQL constraint prevents negative votes."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        attendee = assembly.attendee_ids[0]

        # Confirm attendee
        attendee.action_confirm()

        # Odoo may flush to SQL before @api.constrains; CHECK then raises CheckViolation.
        with self.assertRaises(pg_errors.CheckViolation):
            self.env["assembly.attendee.vote"].create(
                {
                    "attendee_id": attendee.id,
                    "vote_type_id": vote_type.id,
                    "own_votes": -1.0,
                    "delegated_out_votes": 0.0,
                    "delegated_in_votes": 0.0,
                }
            )

    def test_no_delegation_to_non_existing_attendee(self):
        """Constraint prevents delegation to partner who is not an attendee."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]

        # Create a partner who is NOT an attendee
        non_attendee_partner = self._create_partners(self.env, 1, "NonAttendee")[0]
        # pylint: disable=protected-access
        # Try to create delegation to non-attendee (should fail)
        with self.assertRaises(ValidationError) as cm:
            self.env["assembly.delegation"].create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": delegator.partner_id.id,
                    "delegate_partner_id": non_attendee_partner.id,
                    "vote_type_ids": [(6, 0, vote_type.ids)],
                }
            )
        error_msg = str(cm.exception).lower()
        self.assertIn("delegate", error_msg)
        self.assertIn("attendee", error_msg)

    def test_no_effective_delegation_without_confirmed_delegate(self):
        """Delegation row exists but vote transfer waits for a confirmed delegate."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 4)
        self._give_partner_votes(delegate.partner_id, vote_type, 2)
        delegator.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()
        d_line = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        g_line = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(d_line.delegated_out_votes, 0.0)
        self.assertEqual(g_line.delegated_in_votes, 0.0)
        delegate.action_confirm()
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()
        d_line = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        g_line = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(d_line.delegated_out_votes, 4.0)
        self.assertEqual(g_line.delegated_in_votes, 4.0)

    def test_mathematical_consistency_invariant(self):
        """Verify mathematical consistency: total = own + in - out."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]

        # Give votes
        self._give_partner_votes(delegator.partner_id, vote_type, 10)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type, 5)
        # pylint: disable=protected-access
        # Confirm both
        delegator.action_confirm()
        delegate.action_confirm()

        # Create delegation
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )

        # Recompute votes
        assembly.attendee_ids.recompute_attendee_vote_lines()

        # Verify mathematical consistency for delegator
        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        expected_total = (
            av_del.own_votes + av_del.delegated_in_votes - av_del.delegated_out_votes
        )
        self.assertEqual(
            av_del.attendee_vote_total,
            expected_total,
            "Mathematical consistency: total = own + in - out",
        )
        self.assertEqual(av_del.attendee_vote_total, 0.0, "Delegator total is 0")

        # Verify mathematical consistency for delegate
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        expected_total_delegate = (
            av_dec.own_votes + av_dec.delegated_in_votes - av_dec.delegated_out_votes
        )
        self.assertEqual(
            av_dec.attendee_vote_total,
            expected_total_delegate,
            "Mathematical consistency: total = own + in - out",
        )
        self.assertEqual(av_dec.attendee_vote_total, 15.0, "Delegate total is 15")

    def test_vote_conservation_invariant(self):
        """Verify vote conservation: sum of own_votes = sum of total_votes."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]

        # Give votes
        self._give_partner_votes(delegator.partner_id, vote_type, 10)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type, 5)
        # pylint: disable=protected-access
        # Confirm both
        delegator.action_confirm()
        delegate.action_confirm()

        # Create delegation
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )

        # Recompute votes
        assembly.attendee_ids.recompute_attendee_vote_lines()

        # Calculate totals
        total_own_votes = sum(
            av.own_votes
            for attendee in assembly.attendee_ids
            for av in attendee.attendee_vote_ids.filtered(
                lambda v: v.vote_type_id == vote_type
            )
        )
        total_vote_totals = sum(
            av.attendee_vote_total
            for attendee in assembly.attendee_ids
            for av in attendee.attendee_vote_ids.filtered(
                lambda v: v.vote_type_id == vote_type
            )
        )

        # Vote conservation: delegations only transfer votes, never create or destroy
        self.assertEqual(
            total_own_votes,
            total_vote_totals,
            "Vote conservation: sum of own_votes = sum of total_votes",
        )
        self.assertEqual(total_own_votes, 15.0, "Total own votes is 15")

    def test_symmetry_invariant(self):
        """Verify symmetry: delegator loses exactly what delegate gains."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]

        # Give votes
        self._give_partner_votes(delegator.partner_id, vote_type, 10)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type, 5)
        # pylint: disable=protected-access
        # Confirm both
        delegator.action_confirm()
        delegate.action_confirm()

        # Create delegation
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )

        # Recompute votes
        assembly.attendee_ids.recompute_attendee_vote_lines()

        # Verify symmetry
        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Symmetry: delegator loses exactly what delegate gains
        self.assertEqual(
            av_del.delegated_out_votes,
            av_dec.delegated_in_votes,
            "Symmetry: delegator loses exactly what delegate gains",
        )
        self.assertEqual(av_del.delegated_out_votes, 10.0, "Delegator loses 10 votes")
        self.assertEqual(av_dec.delegated_in_votes, 10.0, "Delegate gains 10 votes")

    def test_no_double_counting_invariant(self):
        """Verify no double counting: each delegation affects exactly one delegator \
            and one delegate."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator1 = assembly.attendee_ids[0]
        delegator2 = assembly.attendee_ids[1]
        delegate = assembly.attendee_ids[2]

        # Give votes
        self._give_partner_votes(delegator1.partner_id, vote_type, 10)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator2.partner_id, vote_type, 8)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type, 5)
        # pylint: disable=protected-access
        # Confirm all
        delegator1.action_confirm()
        delegator2.action_confirm()
        delegate.action_confirm()

        # Create two delegations to same delegate
        delegation1 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator1.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        delegation2 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator2.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )

        # Recompute votes
        assembly.attendee_ids.recompute_attendee_vote_lines()

        # Verify no double counting
        av_del1 = delegator1.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_del2 = delegator2.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Each delegation affects exactly one delegator
        self.assertEqual(av_del1.delegated_out_votes, 10.0, "Delegator1 loses 10")
        self.assertEqual(av_del2.delegated_out_votes, 8.0, "Delegator2 loses 8")

        # Delegate receives sum (no double counting)
        self.assertEqual(av_dec.delegated_in_votes, 18.0, "Delegate receives sum")
        self.assertEqual(
            av_dec.delegated_in_votes,
            av_del1.delegated_out_votes + av_del2.delegated_out_votes,
            "No double counting: in = sum of out",
        )

    def test_effective_delegation_invariant(self):
        """Verify effective delegation invariant: out/in > 0 ONLY if
        delegation is effective."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]

        # Give votes
        self._give_partner_votes(delegator.partner_id, vote_type, 10)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type, 5)
        # pylint: disable=protected-access
        # Confirm delegator only
        delegator.action_confirm()

        # Draft delegation while delegate not confirmed (confirmed would be rejected)
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )

        # Recompute votes
        assembly.attendee_ids.recompute_attendee_vote_lines()

        # Verify delegation is NOT effective (delegate not confirmed)
        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(av_del.delegated_out_votes, 0.0, "Not effective: out = 0")
        self.assertEqual(av_dec.delegated_in_votes, 0.0, "Not effective: in = 0")

        # Confirm delegate then confirm delegation: becomes effective
        delegate.action_confirm()
        assembly.attendee_ids.recompute_attendee_vote_lines()

        # Verify delegation is now effective
        av_del_effective = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec_effective = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertGreater(
            av_del_effective.delegated_out_votes, 0.0, "Effective: out > 0"
        )
        self.assertGreater(
            av_dec_effective.delegated_in_votes, 0.0, "Effective: in > 0"
        )
