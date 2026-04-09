# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Production-grade tests for vote edge cases.

Tests complex edge cases that could lead to vote inconsistencies:
- Delegation create / unlink vs vote lines
- Vote type changes in assembly
- Multiple delegations with overlapping vote types
- Delegator and delegate both delegating
- Empty vote types in assembly
- Attendee state transitions during delegation changes
"""

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestVoteEdgeCasesProduction(AssemblyTestMixin, TransactionCase):
    """Production-grade tests for vote edge cases."""

    def test_delegation_create_unlink_vote_lines(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 10)
        self._give_partner_votes(delegate.partner_id, vote_type, 5)
        delegator.action_confirm()
        delegate.action_confirm()
        delegation = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
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
        self.assertEqual(av_del.delegated_out_votes, 10.0)
        self.assertEqual(av_dec.delegated_in_votes, 10.0)
        delegation.unlink()
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()
        av_del = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec = delegate.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(av_del.delegated_out_votes, 0.0)
        self.assertEqual(av_dec.delegated_in_votes, 0.0)

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
            }
        )
        delegation2 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, [vote_type2.id])],
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
            }
        )

        # Delegator2 delegates type2 and type3 (overlapping with delegator1 on type2)
        delegation2 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator2.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, [vote_type2.id, vote_type3.id])],
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
