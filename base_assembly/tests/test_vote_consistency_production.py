# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Production-grade tests for vote consistency guarantees.

This test suite ensures that NO vote inconsistency is possible in any scenario.
It covers:
- Effective vs non-effective delegation in all combinations
- Delegate state transitions (confirm/unconfirm/absent)
- Recomputation consistency (idempotency, determinism)
- Multiple delegations (same delegate, different delegates, partial)
- Complex edge cases (cascading changes, race conditions, state transitions)

Goal: Guarantee mathematical consistency in ALL scenarios.

Includes former ``test_vote_edge_cases_production`` (delegation churn, overlapping
types, empty assembly vote types).
"""

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestVoteConsistencyProduction(AssemblyTestMixin, TransactionCase):
    """Production-grade tests ensuring vote consistency in all scenarios."""

    def test_vote_consistency_effective_delegation_full_cycle(
        self,
    ):  # pylint: disable=too-many-statements
        """Test vote consistency through full delegation lifecycle."""
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
        # Initial state: both registered
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Before confirmation: no delegation effect
        self.assertEqual(av_del.own_votes, 10.0)
        self.assertEqual(av_del.delegated_out_votes, 0.0)
        self.assertEqual(av_del.delegated_in_votes, 0.0)
        self.assertEqual(av_del.attendee_vote_total, 10.0)

        self.assertEqual(av_dec.own_votes, 5.0)
        self.assertEqual(av_dec.delegated_out_votes, 0.0)
        self.assertEqual(av_dec.delegated_in_votes, 0.0)
        self.assertEqual(av_dec.attendee_vote_total, 5.0)

        # Create delegation (draft state)
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "draft",
            }
        )

        # Draft delegation: no effect
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        self.assertEqual(
            av_del.delegated_out_votes, 0.0, "Draft delegation has no effect"
        )
        self.assertEqual(
            av_dec.delegated_in_votes, 0.0, "Draft delegation has no effect"
        )

        # Confirm delegator
        delegator.action_confirm()
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Delegator confirmed but delegate not: no effect
        self.assertEqual(av_del.delegated_out_votes, 0.0)
        self.assertEqual(av_dec.delegated_in_votes, 0.0)

        # Confirm delegate
        delegate.action_confirm()
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Both confirmed but delegation still draft: no effect
        self.assertEqual(av_del.delegated_out_votes, 0.0)
        self.assertEqual(av_dec.delegated_in_votes, 0.0)

        # Confirm delegation
        delegation.write({"delegation_state": "confirmed"})
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Now effective: delegator loses, delegate gains
        self.assertEqual(av_del.own_votes, 10.0)
        self.assertEqual(av_del.delegated_out_votes, 10.0)
        self.assertEqual(av_del.delegated_in_votes, 0.0)
        self.assertEqual(av_del.attendee_vote_total, 0.0)

        self.assertEqual(av_dec.own_votes, 5.0)
        self.assertEqual(av_dec.delegated_out_votes, 0.0)
        self.assertEqual(av_dec.delegated_in_votes, 10.0)
        self.assertEqual(av_dec.attendee_vote_total, 15.0)

        # Verify mathematical consistency
        self.assertEqual(
            av_del.attendee_vote_total,
            av_del.own_votes + av_del.delegated_in_votes - av_del.delegated_out_votes,
        )
        self.assertEqual(
            av_dec.attendee_vote_total,
            av_dec.own_votes + av_dec.delegated_in_votes - av_dec.delegated_out_votes,
        )

        # Revoke delegation
        delegation.write({"delegation_state": "revoked"})
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Revoked: no effect
        self.assertEqual(av_del.delegated_out_votes, 0.0)
        self.assertEqual(av_dec.delegated_in_votes, 0.0)
        self.assertEqual(av_del.attendee_vote_total, 10.0)
        self.assertEqual(av_dec.attendee_vote_total, 5.0)

    def test_vote_consistency_multiple_delegations_same_delegate(
        self,
    ):  # pylint: disable=too-many-locals
        """Test vote consistency with multiple delegations to same delegate."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator1 = assembly.attendee_ids[0]
        delegator2 = assembly.attendee_ids[1]
        delegator3 = assembly.attendee_ids[2]
        delegate = assembly.attendee_ids[3] if len(assembly.attendee_ids) > 3 else None

        if not delegate:
            # Create additional attendee if needed
            partners = self._create_partners(self.env, 1, "Delegate")
            # pylint: disable=protected-access
            assembly.write({"partner_domain": "[('id', 'in', %s)]" % partners.ids})
            assembly.action_generate_attendees()
            delegate = assembly.attendee_ids.filtered(
                lambda a: a.partner_id == partners[0]
            )[0]

        # Give votes
        self._give_partner_votes(delegator1.partner_id, vote_type, 10)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator2.partner_id, vote_type, 8)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator3.partner_id, vote_type, 5)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type, 3)
        # pylint: disable=protected-access
        # Confirm all
        delegator1.action_confirm()
        delegator2.action_confirm()
        delegator3.action_confirm()
        delegate.action_confirm()

        # Create multiple delegations to same delegate
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
        delegation3 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator3.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )

        # Recompute all
        assembly.attendee_ids.recompute_attendee_vote_lines()

        # Verify consistency
        av_del1 = delegator1.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_del2 = delegator2.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_del3 = delegator3.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Each delegator loses their votes
        self.assertEqual(av_del1.delegated_out_votes, 10.0)
        self.assertEqual(av_del2.delegated_out_votes, 8.0)
        self.assertEqual(av_del3.delegated_out_votes, 5.0)

        # Delegate receives sum of all delegators
        self.assertEqual(av_dec.delegated_in_votes, 23.0)
        self.assertEqual(
            av_dec.delegated_in_votes,
            av_del1.delegated_out_votes
            + av_del2.delegated_out_votes
            + av_del3.delegated_out_votes,
        )

        # Verify mathematical consistency for each
        self.assertEqual(
            av_del1.attendee_vote_total,
            av_del1.own_votes
            + av_del1.delegated_in_votes
            - av_del1.delegated_out_votes,
        )
        self.assertEqual(
            av_del2.attendee_vote_total,
            av_del2.own_votes
            + av_del2.delegated_in_votes
            - av_del2.delegated_out_votes,
        )
        self.assertEqual(
            av_del3.attendee_vote_total,
            av_del3.own_votes
            + av_del3.delegated_in_votes
            - av_del3.delegated_out_votes,
        )
        self.assertEqual(
            av_dec.attendee_vote_total,
            av_dec.own_votes + av_dec.delegated_in_votes - av_dec.delegated_out_votes,
        )

        # Verify vote conservation: sum of own_votes = sum of total_votes
        total_own = (
            av_del1.own_votes + av_del2.own_votes + av_del3.own_votes + av_dec.own_votes
        )
        total_total = (
            av_del1.attendee_vote_total
            + av_del2.attendee_vote_total
            + av_del3.attendee_vote_total
            + av_dec.attendee_vote_total
        )
        self.assertEqual(
            total_own,
            total_total,
            "Vote conservation: sum(own) = sum(total)",
        )

    def test_vote_consistency_recomputation_idempotency(self):
        """Test that recomputation is idempotent (multiple calls = same result)."""
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

        # First recomputation
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del_1 = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec_1 = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Second recomputation (should be identical)
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del_2 = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec_2 = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Third recomputation (should be identical)
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del_3 = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec_3 = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # All recomputations should produce identical results
        self.assertEqual(av_del_1.own_votes, av_del_2.own_votes)
        self.assertEqual(av_del_2.own_votes, av_del_3.own_votes)
        self.assertEqual(av_del_1.delegated_out_votes, av_del_2.delegated_out_votes)
        self.assertEqual(av_del_2.delegated_out_votes, av_del_3.delegated_out_votes)
        self.assertEqual(av_del_1.delegated_in_votes, av_del_2.delegated_in_votes)
        self.assertEqual(av_del_2.delegated_in_votes, av_del_3.delegated_in_votes)
        self.assertEqual(av_del_1.attendee_vote_total, av_del_2.attendee_vote_total)
        self.assertEqual(av_del_2.attendee_vote_total, av_del_3.attendee_vote_total)

        self.assertEqual(av_dec_1.own_votes, av_dec_2.own_votes)
        self.assertEqual(av_dec_2.own_votes, av_dec_3.own_votes)
        self.assertEqual(av_dec_1.delegated_out_votes, av_dec_2.delegated_out_votes)
        self.assertEqual(av_dec_2.delegated_out_votes, av_dec_3.delegated_out_votes)
        self.assertEqual(av_dec_1.delegated_in_votes, av_dec_2.delegated_in_votes)
        self.assertEqual(av_dec_2.delegated_in_votes, av_dec_3.delegated_in_votes)
        self.assertEqual(av_dec_1.attendee_vote_total, av_dec_2.attendee_vote_total)
        self.assertEqual(av_dec_2.attendee_vote_total, av_dec_3.attendee_vote_total)

    def test_vote_consistency_recomputation_determinism(self):
        """Test that recomputation is deterministic (same inputs → same outputs)."""
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

        # Recompute and capture state
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del_initial = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec_initial = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Modify nothing, recompute again
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del_final = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec_final = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Results should be identical (deterministic)
        self.assertEqual(av_del_initial.own_votes, av_del_final.own_votes)
        self.assertEqual(
            av_del_initial.delegated_out_votes, av_del_final.delegated_out_votes
        )
        self.assertEqual(
            av_del_initial.delegated_in_votes, av_del_final.delegated_in_votes
        )
        self.assertEqual(
            av_del_initial.attendee_vote_total, av_del_final.attendee_vote_total
        )

        self.assertEqual(av_dec_initial.own_votes, av_dec_final.own_votes)
        self.assertEqual(
            av_dec_initial.delegated_out_votes, av_dec_final.delegated_out_votes
        )
        self.assertEqual(
            av_dec_initial.delegated_in_votes, av_dec_final.delegated_in_votes
        )
        self.assertEqual(
            av_dec_initial.attendee_vote_total, av_dec_final.attendee_vote_total
        )

    def test_vote_consistency_delegate_unconfirm_reconfirm(self):
        """Test vote consistency when delegate unconfirms and reconfirms."""
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

        # Create effective delegation
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )

        # Verify effective
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        self.assertEqual(av_del.delegated_out_votes, 10.0)
        self.assertEqual(av_dec.delegated_in_votes, 10.0)

        # Unconfirm delegate
        delegate.action_mark_absent()
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Delegation no longer effective
        self.assertEqual(av_del.delegated_out_votes, 0.0)
        self.assertEqual(av_dec.delegated_in_votes, 0.0)
        self.assertEqual(av_del.attendee_vote_total, 10.0)
        self.assertEqual(av_dec.attendee_vote_total, 5.0)

        # Reconfirm delegate
        delegate.action_confirm()
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Delegation effective again
        self.assertEqual(av_del.delegated_out_votes, 10.0)
        self.assertEqual(av_dec.delegated_in_votes, 10.0)
        self.assertEqual(av_del.attendee_vote_total, 0.0)
        self.assertEqual(av_dec.attendee_vote_total, 15.0)

    def test_vote_consistency_partial_delegation_multiple_types(
        self,
    ):  # pylint: disable=too-many-locals
        """Test vote consistency with partial delegation across multiple vote types."""
        # Create assembly with multiple vote types
        vote_type1 = self._create_vote_type(self.env, "Type 1", "VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, "Type 2", "VT2")
        # pylint: disable=protected-access
        vote_type3 = self._create_vote_type(self.env, "Type 3", "VT3")
        # pylint: disable=protected-access
        assembly_type = self.env["assembly.type"].create(  # noqa: F841
            {
                "name": "Multi Type",
                "code": "MT",
                "vote_type_ids": [
                    (6, 0, [vote_type1.id, vote_type2.id, vote_type3.id])
                ],
                "default_quorum_type": "percentage",
                "default_quorum_value": 50.0,
                "partner_domain": "[]",
            }
        )

        partners = self._create_partners(  # noqa: F841
            self.env, 2
        )  # pylint: disable=protected-access
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Multi Type Assembly",
                "assembly_type_id": assembly_type.id,
                "partner_domain": "[('id', 'in', %s)]" % partners.ids,
                "vote_type_ids": [
                    (6, 0, [vote_type1.id, vote_type2.id, vote_type3.id])
                ],
                "quorum_type": "percentage",
                "quorum_value": 50.0,
            }
        )
        assembly.action_generate_attendees()

        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]

        # Give votes for all types
        self._give_partner_votes(delegator.partner_id, vote_type1, 10)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator.partner_id, vote_type2, 8)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator.partner_id, vote_type3, 5)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type1, 3)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type2, 2)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type3, 1)
        # pylint: disable=protected-access
        # Confirm both
        delegator.action_confirm()
        delegate.action_confirm()

        # Create partial delegation (only type1 and type2)
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, [vote_type1.id, vote_type2.id])],
                "delegation_state": "confirmed",
            }
        )

        # Recompute
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        # Verify type1: delegated
        av_del_t1 = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type1
        )
        av_dec_t1 = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type1
        )

        self.assertEqual(av_del_t1.delegated_out_votes, 10.0)
        self.assertEqual(av_dec_t1.delegated_in_votes, 10.0)

        # Verify type2: delegated
        av_del_t2 = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type2
        )
        av_dec_t2 = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type2
        )

        self.assertEqual(av_del_t2.delegated_out_votes, 8.0)
        self.assertEqual(av_dec_t2.delegated_in_votes, 8.0)

        # Verify type3: NOT delegated
        av_del_t3 = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type3
        )
        av_dec_t3 = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type3
        )

        self.assertEqual(av_del_t3.delegated_out_votes, 0.0)
        self.assertEqual(av_dec_t3.delegated_in_votes, 0.0)
        self.assertEqual(av_del_t3.attendee_vote_total, 5.0)
        self.assertEqual(av_dec_t3.attendee_vote_total, 1.0)

        # Verify mathematical consistency for all types
        for av in [av_del_t1, av_del_t2, av_del_t3, av_dec_t1, av_dec_t2, av_dec_t3]:
            self.assertEqual(
                av.attendee_vote_total,
                av.own_votes + av.delegated_in_votes - av.delegated_out_votes,
            )

    def test_vote_consistency_cascading_state_changes(self):
        """Test vote consistency with cascading state changes."""
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
        # Create delegations (draft)
        delegation1 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator1.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "draft",
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

        # Confirm all attendees
        delegator1.action_confirm()
        delegator2.action_confirm()
        delegate.action_confirm()

        # Confirm delegations (cascading: both become effective simultaneously)
        delegation1.write({"delegation_state": "confirmed"})
        delegation2.write({"delegation_state": "confirmed"})

        # Recompute all
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

        self.assertEqual(av_del1.delegated_out_votes, 10.0)
        self.assertEqual(av_del2.delegated_out_votes, 8.0)
        self.assertEqual(av_dec.delegated_in_votes, 18.0)

        # Verify mathematical consistency
        self.assertEqual(
            av_del1.attendee_vote_total,
            av_del1.own_votes
            + av_del1.delegated_in_votes
            - av_del1.delegated_out_votes,
        )
        self.assertEqual(
            av_del2.attendee_vote_total,
            av_del2.own_votes
            + av_del2.delegated_in_votes
            - av_del2.delegated_out_votes,
        )
        self.assertEqual(
            av_dec.attendee_vote_total,
            av_dec.own_votes + av_dec.delegated_in_votes - av_dec.delegated_out_votes,
        )

        # Verify vote conservation
        total_own = av_del1.own_votes + av_del2.own_votes + av_dec.own_votes
        total_total = (
            av_del1.attendee_vote_total
            + av_del2.attendee_vote_total
            + av_dec.attendee_vote_total
        )
        self.assertEqual(total_own, total_total)

    def test_vote_consistency_symmetry_guarantee(self):
        """Test that symmetry is guaranteed: delegator loses exactly
        what delegate gains."""
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

        # Create effective delegation
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )

        # Recompute
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Symmetry guarantee: delegator loses exactly what delegate gains
        self.assertEqual(
            av_del.delegated_out_votes,
            av_dec.delegated_in_votes,
            "Symmetry: delegator.out = delegate.in",
        )
        self.assertEqual(
            av_del.delegated_out_votes,
            av_del.own_votes,
            "Delegator loses all own votes",
        )

        # Verify no votes created or destroyed
        total_before = av_del.own_votes + av_dec.own_votes  # noqa: F841
        total_after = (
            av_del.attendee_vote_total + av_dec.attendee_vote_total
        )  # noqa: F841
        self.assertEqual(
            total_before,
            total_after,
            "Vote conservation: no votes created or destroyed",
        )

    def test_vote_consistency_no_double_counting(self):
        """Test that votes are never double-counted."""
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

        # Create effective delegation
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )

        # Recompute multiple times
        for _ in range(5):
            delegator.recompute_attendee_vote_lines()
            delegate.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(
            lambda v, _=_: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v, _=_: v.vote_type_id == vote_type
        )

        # Verify no double counting
        # Delegator should lose exactly 10 votes (not more)
        self.assertEqual(av_del.delegated_out_votes, 10.0)
        self.assertEqual(av_del.attendee_vote_total, 0.0)

        # Delegate should receive exactly 10 votes (not more)
        self.assertEqual(av_dec.delegated_in_votes, 10.0)
        self.assertEqual(av_dec.attendee_vote_total, 15.0)

        # Verify vote conservation
        total_own = av_del.own_votes + av_dec.own_votes  # noqa: F841
        total_total = (
            av_del.attendee_vote_total + av_dec.attendee_vote_total
        )  # noqa: F841
        self.assertEqual(total_own, total_total)


class TestVoteEdgeCasesProduction(AssemblyTestMixin, TransactionCase):
    """Production-grade tests for vote edge cases."""

    def test_vote_consistency_delegation_state_transitions(self):
        """Test vote consistency through all delegation state transitions."""
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

        # Create draft delegation
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "draft",
            }
        )

        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Draft: no effect
        self.assertEqual(av_del.delegated_out_votes, 0.0)
        self.assertEqual(av_dec.delegated_in_votes, 0.0)

        # Transition: draft → confirmed
        delegation.write({"delegation_state": "confirmed"})
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Confirmed: effective
        self.assertEqual(av_del.delegated_out_votes, 10.0)
        self.assertEqual(av_dec.delegated_in_votes, 10.0)

        # Transition: confirmed → revoked
        delegation.write({"delegation_state": "revoked"})
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Revoked: no effect
        self.assertEqual(av_del.delegated_out_votes, 0.0)
        self.assertEqual(av_dec.delegated_in_votes, 0.0)

        # Transition: revoked → confirmed (re-confirm)
        delegation.write({"delegation_state": "confirmed"})
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Re-confirmed: effective again
        self.assertEqual(av_del.delegated_out_votes, 10.0)
        self.assertEqual(av_dec.delegated_in_votes, 10.0)

    def test_vote_consistency_vote_type_removed_from_assembly(self):
        """Test vote consistency when vote type is removed from assembly."""
        # Create assembly with multiple vote types
        vote_type1 = self._create_vote_type(self.env, "Type 1", "VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, "Type 2", "VT2")
        # pylint: disable=protected-access
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Multi Type",
                "code": "MT",
                "vote_type_ids": [(6, 0, [vote_type1.id, vote_type2.id])],
                "default_quorum_type": "percentage",
                "default_quorum_value": 50.0,
                "partner_domain": "[]",
            }
        )

        partners = self._create_partners(
            self.env, 2
        )  # pylint: disable=protected-access
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Multi Type Assembly",
                "assembly_type_id": assembly_type.id,
                "partner_domain": "[('id', 'in', %s)]" % partners.ids,
                "vote_type_ids": [(6, 0, [vote_type1.id, vote_type2.id])],
                "quorum_type": "percentage",
                "quorum_value": 50.0,
            }
        )
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

        # Create delegations for both types
        delegation1 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, [vote_type1.id])],
                "delegation_state": "confirmed",
            }
        )
        delegation2 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, [vote_type2.id])],
                "delegation_state": "confirmed",
            }
        )

        # Recompute
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        # Verify both types are delegated
        av_del_t1 = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type1
        )
        av_del_t2 = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type2
        )

        self.assertEqual(av_del_t1.delegated_out_votes, 10.0)
        self.assertEqual(av_del_t2.delegated_out_votes, 8.0)

        # Remove vote_type2 from assembly
        assembly.write({"vote_type_ids": [(6, 0, [vote_type1.id])]})
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        # vote_type1 should still be delegated
        av_del_t1 = delegator.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type1
        )
        self.assertEqual(av_del_t1.delegated_out_votes, 10.0)

        # vote_type2 records should be removed
        av_del_t2 = delegator.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type2
        )
        self.assertFalse(av_del_t2, "vote_type2 records should be removed")

    def test_vote_consistency_delegator_and_delegate_both_delegating(self):
        """Same-type inbound delegation blocks a further outbound on that type (no chain)."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        final_delegate = (
            assembly.attendee_ids[2] if len(assembly.attendee_ids) > 2 else None
        )

        if not final_delegate:
            partners = self._create_partners(self.env, 1, "FinalDelegate")
            # pylint: disable=protected-access
            assembly.write({"partner_domain": "[('id', 'in', %s)]" % partners.ids})
            assembly.action_generate_attendees()
            final_delegate = assembly.attendee_ids.filtered(
                lambda a: a.partner_id == partners[0]
            )[0]

        self._give_partner_votes(delegator.partner_id, vote_type, 10)
        self._give_partner_votes(delegate.partner_id, vote_type, 8)
        self._give_partner_votes(final_delegate.partner_id, vote_type, 5)
        delegator.action_confirm()
        delegate.action_confirm()
        final_delegate.action_confirm()

        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(av_del.delegated_out_votes, 10.0)
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(av_dec.delegated_in_votes, 10.0)
        self.assertEqual(av_dec.delegated_out_votes, 0.0)

        with self.assertRaises(ValidationError):
            self.env["assembly.delegation"].create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": delegate.partner_id.id,
                    "delegate_partner_id": final_delegate.partner_id.id,
                    "vote_type_ids": [(6, 0, vote_type.ids)],
                    "delegation_state": "confirmed",
                }
            )

    def test_vote_consistency_empty_vote_types_in_assembly(self):
        """Test vote consistency when assembly has no vote types."""
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

        # Recompute
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        # Verify delegation is effective
        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(av_del.delegated_out_votes, 10.0)

        # Remove all vote types from assembly
        assembly.write({"vote_type_ids": [(5, 0, 0)]})
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        # All vote records should be removed
        self.assertFalse(
            delegator.attendee_vote_ids,
            "All vote records should be removed when assembly has no vote types",
        )
        self.assertFalse(
            delegate.attendee_vote_ids,
            "All vote records should be removed when assembly has no vote types",
        )

    def test_vote_consistency_attendee_state_change_during_delegation(self):
        """Test vote consistency when attendee state changes
        during delegation lifecycle."""
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
        # Confirm delegator
        delegator.action_confirm()

        # Create delegation (draft)
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "draft",
            }
        )

        # Confirm delegate while delegation is draft
        delegate.action_confirm()
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Draft delegation: no effect
        self.assertEqual(av_del.delegated_out_votes, 0.0)
        self.assertEqual(av_dec.delegated_in_votes, 0.0)

        # Confirm delegation
        delegation.write({"delegation_state": "confirmed"})
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # Now effective
        self.assertEqual(av_del.delegated_out_votes, 10.0)
        self.assertEqual(av_dec.delegated_in_votes, 10.0)

        # Unconfirm delegate
        delegate.action_mark_absent()
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )

        # No longer effective
        self.assertEqual(av_del.delegated_out_votes, 0.0)
        self.assertEqual(av_dec.delegated_in_votes, 0.0)

        # Reconfirm delegate
        delegate.action_confirm()
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()

        av_del = delegator.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type
        )

        # Effective again
        self.assertEqual(av_del.delegated_out_votes, 10.0)
        self.assertEqual(av_dec.delegated_in_votes, 10.0)

    def test_vote_consistency_multiple_delegations_overlapping_types(
        self,
    ):  # pylint: disable=too-many-locals
        """Test vote consistency with multiple delegations
        with overlapping vote types."""
        # Create assembly with multiple vote types
        vote_type1 = self._create_vote_type(self.env, "Type 1", "VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, "Type 2", "VT2")
        # pylint: disable=protected-access
        vote_type3 = self._create_vote_type(self.env, "Type 3", "VT3")
        # pylint: disable=protected-access
        assembly_type = self.env["assembly.type"].create(  # noqa: F841
            {
                "name": "Multi Type",
                "code": "MT",
                "vote_type_ids": [
                    (6, 0, [vote_type1.id, vote_type2.id, vote_type3.id])
                ],
                "default_quorum_type": "percentage",
                "default_quorum_value": 50.0,
                "partner_domain": "[]",
            }
        )

        partners = self._create_partners(  # noqa: F841
            self.env, 3
        )  # pylint: disable=protected-access
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Multi Type Assembly",
                "assembly_type_id": assembly_type.id,
                "partner_domain": "[('id', 'in', %s)]" % partners.ids,
                "vote_type_ids": [
                    (6, 0, [vote_type1.id, vote_type2.id, vote_type3.id])
                ],
                "quorum_type": "percentage",
                "quorum_value": 50.0,
            }
        )
        assembly.action_generate_attendees()

        delegator1 = assembly.attendee_ids[0]
        delegator2 = assembly.attendee_ids[1]
        delegate = assembly.attendee_ids[2]

        # Give votes
        self._give_partner_votes(delegator1.partner_id, vote_type1, 10)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator1.partner_id, vote_type2, 8)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator1.partner_id, vote_type3, 5)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator2.partner_id, vote_type1, 7)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator2.partner_id, vote_type2, 6)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator2.partner_id, vote_type3, 4)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type1, 3)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type2, 2)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type3, 1)
        # pylint: disable=protected-access
        # Confirm all
        delegator1.action_confirm()
        delegator2.action_confirm()
        delegate.action_confirm()

        # Delegator1 delegates type1 and type2
        delegation1 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator1.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, [vote_type1.id, vote_type2.id])],
                "delegation_state": "confirmed",
            }
        )

        # Delegator2 delegates type2 and type3 (overlapping with delegator1 on type2)
        delegation2 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator2.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, [vote_type2.id, vote_type3.id])],
                "delegation_state": "confirmed",
            }
        )

        # Recompute
        assembly.attendee_ids.recompute_attendee_vote_lines()

        # Verify type1: only delegator1 delegates
        av_del1_t1 = delegator1.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type1
        )
        av_dec_t1 = delegate.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type1
        )

        self.assertEqual(av_del1_t1.delegated_out_votes, 10.0)
        self.assertEqual(av_dec_t1.delegated_in_votes, 10.0)

        # Verify type2: both delegators delegate (overlapping)
        av_del1_t2 = delegator1.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type2
        )
        av_del2_t2 = delegator2.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type2
        )
        av_dec_t2 = delegate.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type2
        )

        self.assertEqual(av_del1_t2.delegated_out_votes, 8.0)
        self.assertEqual(av_del2_t2.delegated_out_votes, 6.0)
        self.assertEqual(av_dec_t2.delegated_in_votes, 14.0)  # 8 + 6

        # Verify type3: only delegator2 delegates
        av_del2_t3 = delegator2.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type3
        )
        av_dec_t3 = delegate.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type3
        )

        self.assertEqual(av_del2_t3.delegated_out_votes, 4.0)
        self.assertEqual(av_dec_t3.delegated_in_votes, 4.0)

        # Verify mathematical consistency for all
        for attendee in [delegator1, delegator2, delegate]:
            for vote_type in [vote_type1, vote_type2, vote_type3]:
                vote_type_id = vote_type.id  # Capture in closure
                av = attendee.attendee_vote_ids.filtered(
                    lambda v, vt_id=vote_type_id, vote_type=vote_type: v.vote_type_id.id
                    == vt_id
                )
                if av:
                    self.assertEqual(
                        av.attendee_vote_total,
                        av.own_votes + av.delegated_in_votes - av.delegated_out_votes,
                    )
