# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Production-grade tests for recomputation consistency across multiple changes.

Tests that vote recomputation remains consistent when:
- Multiple delegations are created/modified simultaneously
- Attendees confirm/unconfirm in sequence
- Vote types are added/removed from assembly
- Multiple cascading changes occur
"""

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestRecomputationMultipleChanges(AssemblyTestMixin, TransactionCase):
    """Test recomputation consistency across multiple simultaneous changes."""

    def test_recomputation_consistency_multiple_delegations_created(self):
        """Recomputation remains consistent when multiple delegations
        created simultaneously."""
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

        # Create multiple delegations simultaneously
        delegation1 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator1.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        delegation2 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator2.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )

        # Recompute all attendees
        assembly.attendee_ids.recompute_attendee_vote_lines()

        # Verify consistency
        av_del1 = delegator1.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_del2 = delegator2.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Mathematical consistency check
        self.assertEqual(av_del1.delegated_out_votes, 10.0, "Delegator1 loses votes")
        self.assertEqual(av_del2.delegated_out_votes, 8.0, "Delegator2 loses votes")
        self.assertEqual(av_dec.delegated_in_votes, 18.0, "Delegate receives sum")
        self.assertEqual(
            av_dec.delegated_in_votes,
            av_del1.delegated_out_votes + av_del2.delegated_out_votes,
            "Mathematical consistency: in = sum of out",
        )

    def test_recomputation_consistency_sequential_confirmations(self):
        """Recomputation remains consistent across sequential confirmations."""
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
        # Confirm delegate first (required for confirmed delegations)
        delegate.action_confirm()

        # Create delegations
        delegation1 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator1.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        delegation2 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator2.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )

        # Sequential confirmations
        delegator1.action_confirm()  # Step 1
        delegator2.action_confirm()  # Step 2
        delegate.action_confirm()  # Step 3: both delegations become effective

        # Final recomputation
        assembly.attendee_ids.recompute_attendee_vote_lines()

        # Verify consistency after all changes
        av_del1 = delegator1.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_del2 = delegator2.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Mathematical consistency
        total_delegated_out = av_del1.delegated_out_votes + av_del2.delegated_out_votes
        self.assertEqual(
            av_dec.delegated_in_votes,
            total_delegated_out,
            "Mathematical consistency: in = sum of out",
        )
        self.assertEqual(av_dec.delegated_in_votes, 18.0, "Delegate receives 18 votes")

    def test_recomputation_consistency_vote_type_changes(self):
        """Recomputation remains consistent when vote types are added/removed."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        vote_type1 = assembly.assembly_type_id.vote_type_ids[0]
        vote_type2 = self._create_vote_type(self.env, name="VT2")
        # pylint: disable=protected-access
        assembly.action_generate_attendees()
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]

        # Give votes for both types
        self._give_partner_votes(delegator.partner_id, vote_type1, 10)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator.partner_id, vote_type2, 8)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type1, 5)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type2, 3)
        # pylint: disable=protected-access
        # Confirm both
        delegator.action_confirm()
        delegate.action_confirm()

        # Create delegation for vote_type1 only
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type1.ids)],
                "delegation_state": "confirmed",
            }
        )

        # Add vote_type2 to assembly
        assembly.write({"vote_type_ids": [(4, vote_type2.id)]})

        # Recompute: should handle new vote type correctly
        assembly.attendee_ids.recompute_attendee_vote_lines()

        # Verify vote_type1: delegation effective
        av_del_vt1 = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type1
        )
        av_dec_vt1 = delegate.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type1
        )
        self.assertEqual(
            av_del_vt1.delegated_out_votes, 10.0, "VT1: delegator loses votes"
        )
        self.assertEqual(
            av_dec_vt1.delegated_in_votes, 10.0, "VT1: delegate receives votes"
        )

        # Verify vote_type2: delegation NOT effective (not in delegation)
        av_del_vt2 = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type2
        )
        av_dec_vt2 = delegate.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type2
        )
        self.assertEqual(
            av_del_vt2.delegated_out_votes, 0.0, "VT2: delegator keeps votes"
        )
        self.assertEqual(
            av_dec_vt2.delegated_in_votes, 0.0, "VT2: delegate doesn't receive"
        )

        # Remove vote_type1 from assembly
        assembly.write({"vote_type_ids": [(3, vote_type1.id)]})

        # Recompute: vote_type1 records should be removed
        assembly.attendee_ids.recompute_attendee_vote_lines()

        # Verify vote_type1 records are removed
        av_del_vt1 = delegator.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type1
        )
        self.assertFalse(
            av_del_vt1, "VT1 records removed when type removed from assembly"
        )

        # Verify vote_type2 still exists
        av_del_vt2 = delegator.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type2
        )
        self.assertTrue(av_del_vt2, "VT2 records still exist")

    def test_recomputation_consistency_multiple_state_changes(self):
        """Recomputation remains consistent across multiple delegation state changes."""
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
                "delegation_state": "confirmed",
            }
        )

        # Multiple state changes
        delegation.write({"delegation_state": "revoked"})  # Step 1: revoke
        assembly.attendee_ids.recompute_attendee_vote_lines()
        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(av_del.delegated_out_votes, 0.0, "Revoked: no effect")

        delegation.write({"delegation_state": "confirmed"})  # Step 2: re-confirm
        assembly.attendee_ids.recompute_attendee_vote_lines()
        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(av_del.delegated_out_votes, 10.0, "Re-confirmed: effective")

        delegation.write({"delegation_state": "revoked"})  # Step 3: revoke again
        assembly.attendee_ids.recompute_attendee_vote_lines()
        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(av_del.delegated_out_votes, 0.0, "Revoked again: no effect")

        # Final consistency check
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(
            av_dec.delegated_in_votes, 0.0, "Delegate has no delegated votes"
        )
        self.assertEqual(av_del.attendee_vote_total, 10.0, "Delegator total is 10")
        self.assertEqual(av_dec.attendee_vote_total, 5.0, "Delegate total is 5")

    def test_recomputation_consistency_complex_scenario(self):
        """Recomputation remains consistent in complex multi-step scenario."""
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
        # Step 1: Create delegations (not effective yet - delegate not confirmed)
        delegation1 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator1.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "draft",  # Start as draft
            }
        )
        delegation2 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator2.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "draft",
            }
        )

        # Step 2: Confirm delegator1 (delegation still not effective - delegate not confirmed)
        delegator1.action_confirm()
        assembly.attendee_ids.recompute_attendee_vote_lines()
        av_del1 = delegator1.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(
            av_del1.delegated_out_votes, 0.0, "No effect: delegate not confirmed"
        )

        # Step 3: Confirm delegate and confirm delegation1 (becomes effective)
        delegate.action_confirm()
        delegation1.write({"delegation_state": "confirmed"})
        assembly.attendee_ids.recompute_attendee_vote_lines()
        av_del1 = delegator1.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(av_del1.delegated_out_votes, 10.0, "Delegation1 effective")
        self.assertEqual(
            av_dec.delegated_in_votes, 10.0, "Delegate receives from delegator1"
        )

        # Step 4: Confirm delegator2 and confirm delegation2
        delegator2.action_confirm()
        delegation2.write({"delegation_state": "confirmed"})
        assembly.attendee_ids.recompute_attendee_vote_lines()
        av_del2 = delegator2.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(av_del2.delegated_out_votes, 8.0, "Delegation2 effective")
        self.assertEqual(av_dec.delegated_in_votes, 18.0, "Delegate receives from both")

        # Step 5: Revoke delegation1
        delegation1.write({"delegation_state": "revoked"})
        assembly.attendee_ids.recompute_attendee_vote_lines()
        av_del1 = delegator1.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(av_del1.delegated_out_votes, 0.0, "Delegation1 revoked")
        self.assertEqual(
            av_dec.delegated_in_votes, 8.0, "Delegate receives only from delegator2"
        )

        # Final consistency check
        total_own = (  # noqa: F841
            delegator1.attendee_vote_ids.filtered(
                lambda v: v.vote_type_id == vote_type
            ).own_votes
            + delegator2.attendee_vote_ids.filtered(
                lambda v: v.vote_type_id == vote_type
            ).own_votes
            + delegate.attendee_vote_ids.filtered(
                lambda v: v.vote_type_id == vote_type
            ).own_votes
        )
        total_delegated_out = (  # noqa: F841
            delegator1.attendee_vote_ids.filtered(
                lambda v: v.vote_type_id == vote_type
            ).delegated_out_votes
            + delegator2.attendee_vote_ids.filtered(
                lambda v: v.vote_type_id == vote_type
            ).delegated_out_votes
        )
        total_delegated_in = delegate.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type
        ).delegated_in_votes

        self.assertEqual(
            total_delegated_out,
            total_delegated_in,
            "Mathematical consistency: total out = total in",
        )
        self.assertEqual(total_own, 23.0, "Total own votes is 23")
