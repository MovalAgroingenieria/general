# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Production-grade tests for edge cases with multiple vote types.

Tests complex scenarios involving:
- Multiple vote types in assembly
- Partial delegations (some types delegated, others not)
- Delegations covering all types vs specific types
- Vote type changes in assembly
- Multiple delegations with different type coverage
"""

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestMultipleVoteTypesEdgeCases(AssemblyTestMixin, TransactionCase):
    """Test edge cases with multiple vote types."""

    def test_partial_delegation_multiple_types(self):
        """Delegation can cover only some vote types, leaving others unaffected."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        # Create assembly with multiple vote types
        vote_type1 = self._create_vote_type(self.env, name="VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, name="VT2")
        # pylint: disable=protected-access
        vote_type3 = self._create_vote_type(self.env, name="VT3")
        # pylint: disable=protected-access
        # pylint: disable=protected-access
        assembly_type = self._create_assembly_type(
            self.env, name="Multi Type", vote_type=vote_type1
        )
        assembly_type.vote_type_ids = [(4, vote_type2.id), (4, vote_type3.id)]
        assembly.assembly_type_id = assembly_type
        assembly.vote_type_ids = [(6, 0, [vote_type1.id, vote_type2.id, vote_type3.id])]
        assembly.action_generate_attendees()

        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]

        # Give votes for all types
        self._give_partner_votes(delegator.partner_id, vote_type1, 10)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator.partner_id, vote_type2, 8)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator.partner_id, vote_type3, 6)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type1, 5)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type2, 3)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type3, 2)
        # pylint: disable=protected-access
        # Confirm both
        delegator.action_confirm()
        delegate.action_confirm()

        # Create delegation for only vote_type1 and vote_type2
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, [vote_type1.id, vote_type2.id])],
                "delegation_state": "confirmed",
            }
        )

        # Recompute votes
        assembly.attendee_ids.recompute_attendee_vote_lines()

        # Verify vote_type1: delegation effective
        av_del_vt1 = delegator.attendee_vote_ids.filtered(  # noqa: F841
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

        # Verify vote_type2: delegation effective
        av_del_vt2 = delegator.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type2
        )
        av_dec_vt2 = delegate.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type2
        )
        self.assertEqual(
            av_del_vt2.delegated_out_votes, 8.0, "VT2: delegator loses votes"
        )
        self.assertEqual(
            av_dec_vt2.delegated_in_votes, 8.0, "VT2: delegate receives votes"
        )

        # Verify vote_type3: delegation NOT effective (not in delegation)
        av_del_vt3 = delegator.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type3
        )
        av_dec_vt3 = delegate.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type3
        )
        self.assertEqual(
            av_del_vt3.delegated_out_votes, 0.0, "VT3: delegator keeps votes"
        )
        self.assertEqual(
            av_dec_vt3.delegated_in_votes, 0.0, "VT3: delegate doesn't receive"
        )

    def test_delegation_all_types_vs_specific_types(
        self,
    ):  # pylint: disable=too-many-locals
        """Compare delegation with all types (empty vote_type_ids) vs specific types."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        vote_type1 = self._create_vote_type(self.env, name="VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, name="VT2")
        # pylint: disable=protected-access
        assembly_type = self._create_assembly_type(
            self.env, name="Multi Type", vote_type=vote_type1
        )
        assembly_type.vote_type_ids = [(4, vote_type2.id)]
        assembly.assembly_type_id = assembly_type
        assembly.vote_type_ids = [(6, 0, [vote_type1.id, vote_type2.id])]
        assembly.action_generate_attendees()

        delegator1 = assembly.attendee_ids[0]
        delegator2 = assembly.attendee_ids[1]
        delegate = assembly.attendee_ids[2]

        # Give votes
        self._give_partner_votes(delegator1.partner_id, vote_type1, 10)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator1.partner_id, vote_type2, 8)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator2.partner_id, vote_type1, 6)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator2.partner_id, vote_type2, 4)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type1, 5)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type2, 3)
        # pylint: disable=protected-access
        # Confirm all
        delegator1.action_confirm()
        delegator2.action_confirm()
        delegate.action_confirm()

        # Delegation1: all types (empty vote_type_ids)
        delegation1 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator1.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [],  # Empty = all types
                "delegation_state": "confirmed",
            }
        )

        # Delegation2: only vote_type1
        delegation2 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator2.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type1.ids)],
                "delegation_state": "confirmed",
            }
        )

        # Recompute votes
        assembly.attendee_ids.recompute_attendee_vote_lines()

        # Verify delegation1 (all types)
        av_del1_vt1 = delegator1.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type1
        )
        av_del1_vt2 = delegator1.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type2
        )
        self.assertEqual(av_del1_vt1.delegated_out_votes, 10.0, "Delegator1 loses VT1")
        self.assertEqual(av_del1_vt2.delegated_out_votes, 8.0, "Delegator1 loses VT2")

        # Verify delegation2 (only vote_type1)
        av_del2_vt1 = delegator2.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type1
        )
        av_del2_vt2 = delegator2.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type2
        )
        self.assertEqual(av_del2_vt1.delegated_out_votes, 6.0, "Delegator2 loses VT1")
        self.assertEqual(av_del2_vt2.delegated_out_votes, 0.0, "Delegator2 keeps VT2")

        # Verify delegate receives from both delegations
        av_dec_vt1 = delegate.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type1
        )
        av_dec_vt2 = delegate.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type2
        )
        self.assertEqual(
            av_dec_vt1.delegated_in_votes, 16.0, "Delegate receives VT1 from both"
        )
        self.assertEqual(
            av_dec_vt2.delegated_in_votes, 8.0, "Delegate receives VT2 from delegator1"
        )

    def test_vote_type_removed_from_assembly(self):
        """Vote records are cleaned up when vote type is removed from assembly."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        vote_type1 = self._create_vote_type(self.env, name="VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, name="VT2")
        assembly_type = self._create_assembly_type(
            # pylint: disable=protected-access
            self.env,
            name="Multi Type",
            vote_type=vote_type1,
        )
        assembly_type.vote_type_ids = [(4, vote_type2.id)]
        assembly.assembly_type_id = assembly_type
        assembly.vote_type_ids = [(6, 0, [vote_type1.id, vote_type2.id])]
        assembly.action_generate_attendees()

        attendee = assembly.attendee_ids[0]

        # Give votes for both types
        self._give_partner_votes(attendee.partner_id, vote_type1, 10)
        # pylint: disable=protected-access
        self._give_partner_votes(attendee.partner_id, vote_type2, 8)
        # pylint: disable=protected-access
        # Confirm attendee
        attendee.action_confirm()

        # Recompute: should create vote records for both types
        attendee.recompute_attendee_vote_lines()
        av_vt1 = attendee.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type1
        )
        av_vt2 = attendee.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type2
        )
        self.assertTrue(av_vt1, "VT1 record exists")
        self.assertTrue(av_vt2, "VT2 record exists")

        # Remove vote_type2 from assembly
        assembly.write({"vote_type_ids": [(3, vote_type2.id)]})

        # Recompute: vote_type2 record should be removed
        attendee.recompute_attendee_vote_lines()
        av_vt1 = attendee.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type1
        )
        av_vt2 = attendee.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type2
        )
        self.assertTrue(av_vt1, "VT1 record still exists")
        self.assertFalse(av_vt2, "VT2 record removed")

    def test_multiple_delegations_different_type_coverage(
        self,
    ):  # pylint: disable=too-many-locals
        """Multiple delegations with different type coverage work correctly."""
        partners = self._create_partners(self.env, 4, "MVPartner")
        partner_domain = "[('id', 'in', %s)]" % partners.ids
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                partner_domain=partner_domain,
            )
        )
        vote_type1 = self._create_vote_type(self.env, name="VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, name="VT2")
        # pylint: disable=protected-access
        vote_type3 = self._create_vote_type(self.env, name="VT3")
        # pylint: disable=protected-access
        assembly_type = self._create_assembly_type(
            self.env, name="Multi Type", vote_type=vote_type1
        )
        assembly_type.vote_type_ids = [(4, vote_type2.id), (4, vote_type3.id)]
        assembly.assembly_type_id = assembly_type
        assembly.vote_type_ids = [(6, 0, [vote_type1.id, vote_type2.id, vote_type3.id])]
        assembly.action_generate_attendees()

        delegator1 = assembly.attendee_ids[0]
        delegator2 = assembly.attendee_ids[1]
        delegator3 = assembly.attendee_ids[2]
        delegate_attendee = assembly.attendee_ids[3]

        # Give votes
        self._give_partner_votes(delegator1.partner_id, vote_type1, 10)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator1.partner_id, vote_type2, 8)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator2.partner_id, vote_type2, 6)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator2.partner_id, vote_type3, 4)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator3.partner_id, vote_type1, 5)
        # pylint: disable=protected-access
        self._give_partner_votes(delegator3.partner_id, vote_type3, 3)
        # pylint: disable=protected-access
        # Confirm all
        delegator1.action_confirm()
        delegator2.action_confirm()
        delegator3.action_confirm()
        delegate_attendee.action_confirm()

        # Delegation1: vote_type1 and vote_type2
        delegation1 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator1.partner_id.id,
                "delegate_partner_id": delegate_attendee.partner_id.id,
                "vote_type_ids": [(6, 0, [vote_type1.id, vote_type2.id])],
                "delegation_state": "confirmed",
            }
        )

        # Delegation2: vote_type2 and vote_type3
        delegation2 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator2.partner_id.id,
                "delegate_partner_id": delegate_attendee.partner_id.id,
                "vote_type_ids": [(6, 0, [vote_type2.id, vote_type3.id])],
                "delegation_state": "confirmed",
            }
        )

        # Delegation3: vote_type1 and vote_type3
        delegation3 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator3.partner_id.id,
                "delegate_partner_id": delegate_attendee.partner_id.id,
                "vote_type_ids": [(6, 0, [vote_type1.id, vote_type3.id])],
                "delegation_state": "confirmed",
            }
        )

        # Recompute votes
        assembly.attendee_ids.recompute_attendee_vote_lines()

        # Verify delegate receives votes for each type
        av_dec_vt1 = delegate_attendee.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type1
        )
        av_dec_vt2 = delegate_attendee.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type2
        )
        av_dec_vt3 = delegate_attendee.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type3
        )

        # vote_type1: from delegator1 and delegator3
        self.assertEqual(
            av_dec_vt1.delegated_in_votes, 15.0, "VT1: from delegator1 and delegator3"
        )

        # vote_type2: from delegator1 and delegator2
        self.assertEqual(
            av_dec_vt2.delegated_in_votes, 14.0, "VT2: from delegator1 and delegator2"
        )

        # vote_type3: from delegator2 and delegator3
        self.assertEqual(
            av_dec_vt3.delegated_in_votes, 7.0, "VT3: from delegator2 and delegator3"
        )
