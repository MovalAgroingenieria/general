# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Vote recomputation: consistency, determinism, and persisted-row regression.

Includes former ``test_vote_recomputation_regression`` (search-based persisted
``assembly.attendee.vote``) and ``test_recomputation_multiple_changes`` (multi-step
delegation / vote-type churn).
"""

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestVoteRecomputationConsistency(AssemblyTestMixin, TransactionCase):
    """Test vote recomputation consistency and determinism."""

    def test_recomputation_is_deterministic(self):
        """Multiple recomputations produce same result."""
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
        av_dec_1 = delegate.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type
        )
        result_1 = (av_del_1.delegated_out_votes, av_dec_1.delegated_in_votes)

        # Second recomputation (should be same)
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()
        av_del_2 = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        av_dec_2 = delegate.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type
        )
        result_2 = (
            av_del_2.delegated_out_votes,
            av_dec_2.delegated_in_votes,
        )  # noqa: F841

        # Results should be identical
        self.assertEqual(result_1, result_2, "Recomputation should be deterministic")
        self.assertEqual(result_1[0], 10.0, "Delegator should lose 10 votes")
        self.assertEqual(result_1[1], 10.0, "Delegate should receive 10 votes")

    def test_recomputation_is_idempotent(self):
        """Multiple calls to recompute_votes() produce same result."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        attendee = assembly.attendee_ids[0]

        # Give votes
        self._give_partner_votes(attendee.partner_id, vote_type, 10)
        # pylint: disable=protected-access
        # Confirm
        attendee.action_confirm()

        # Recompute multiple times
        attendee.recompute_attendee_vote_lines()
        av_1 = attendee.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type
        )
        total_1 = av_1.attendee_vote_total

        attendee.recompute_attendee_vote_lines()
        av_2 = attendee.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type
        )
        total_2 = av_2.attendee_vote_total

        attendee.recompute_attendee_vote_lines()
        av_3 = attendee.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type
        )
        total_3 = av_3.attendee_vote_total  # noqa: F841

        # All should be same
        self.assertEqual(total_1, total_2, "Idempotent: call 1 = call 2")
        self.assertEqual(total_2, total_3, "Idempotent: call 2 = call 3")
        self.assertEqual(total_1, 10.0, "Total should be 10")

    def test_recomputation_is_complete_all_vote_types(self):
        """Recomputation processes all vote types for all attendees."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        # Create assembly with multiple vote types
        vote_type1 = self._create_vote_type(self.env, name="VT1", code="VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Multi Type",
                "code": "MULTI",
                "vote_type_ids": [(6, 0, [vote_type1.id, vote_type2.id])],
                "default_quorum_type": "percentage",
                "default_quorum_value": 50.0,
                "default_quorum_second_call_type": "any",
                "default_quorum_second_call_value": 0.0,
                "partner_domain": "[]",
            }
        )
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Multi Type Assembly",
                "assembly_type_id": assembly_type.id,
            }
        )
        assembly.action_generate_attendees()
        attendee = assembly.attendee_ids[0]

        # Give votes for both types
        self._give_partner_votes(attendee.partner_id, vote_type1, 10)
        # pylint: disable=protected-access
        self._give_partner_votes(attendee.partner_id, vote_type2, 5)
        # pylint: disable=protected-access
        # Confirm
        attendee.action_confirm()

        # Recompute
        attendee.recompute_attendee_vote_lines()

        # Verify both vote types were processed
        av_t1 = attendee.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type1
        )
        av_t2 = attendee.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type2
        )

        self.assertTrue(av_t1, "Vote type 1 should exist")
        self.assertTrue(av_t2, "Vote type 2 should exist")
        self.assertEqual(av_t1.own_votes, 10.0, "Type1: 10 votes")
        self.assertEqual(av_t2.own_votes, 5.0, "Type2: 5 votes")

    def test_recomputation_handles_vote_type_removal(self):
        """Recomputation removes obsolete vote records when vote types removed."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        # Create assembly with multiple vote types
        vote_type1 = self._create_vote_type(self.env, name="VT1", code="VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Multi Type",
                "code": "MULTI",
                "vote_type_ids": [(6, 0, [vote_type1.id, vote_type2.id])],
                "default_quorum_type": "percentage",
                "default_quorum_value": 50.0,
                "default_quorum_second_call_type": "any",
                "default_quorum_second_call_value": 0.0,
                "partner_domain": "[]",
            }
        )
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Multi Type Assembly",
                "assembly_type_id": assembly_type.id,
            }
        )
        assembly.action_generate_attendees()
        attendee = assembly.attendee_ids[0]

        # Give votes for both types
        self._give_partner_votes(attendee.partner_id, vote_type1, 10)
        # pylint: disable=protected-access
        self._give_partner_votes(attendee.partner_id, vote_type2, 5)
        # pylint: disable=protected-access
        # Confirm and recompute
        attendee.action_confirm()
        attendee.recompute_attendee_vote_lines()

        # Verify both exist
        av_t1 = attendee.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type1
        )
        av_t2 = attendee.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type2
        )
        self.assertTrue(av_t1, "Type1 should exist")
        self.assertTrue(av_t2, "Type2 should exist")

        # Remove vote_type2 from assembly
        assembly.vote_type_ids = [(6, 0, [vote_type1.id])]

        # Recompute (should remove type2 record)
        attendee.recompute_attendee_vote_lines()

        # Verify type1 still exists, type2 removed
        av_t1 = attendee.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type1
        )
        av_t2 = attendee.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type2
        )
        self.assertTrue(av_t1, "Type1 should still exist")
        self.assertFalse(av_t2, "Type2 should be removed")

    def test_recomputation_consistency_across_state_changes(self):
        """Recomputation is consistent across attendee state changes."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]

        # Give votes
        self._give_partner_votes(delegator.partner_id, vote_type, 10)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type, 5)
        # pylint: disable=protected-access
        # Create delegation (draft, not effective yet)
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "draft",
            }
        )

        # State 1: Both registered (no effect)
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()
        av_del_1 = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(av_del_1.delegated_out_votes, 0.0, "State 1: no effect")
        out_after_state_1 = av_del_1.delegated_out_votes

        # State 2: Delegator confirmed (still no effect, delegate not confirmed)
        delegator.action_confirm()
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()
        av_del_2 = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(av_del_2.delegated_out_votes, 0.0, "State 2: no effect")
        out_after_state_2 = av_del_2.delegated_out_votes

        # State 3: Both confirmed and delegation confirmed (effective)
        delegate.action_confirm()
        delegation.write({"delegation_state": "confirmed"})
        assembly.attendee_ids.recompute_attendee_vote_lines()
        av_del_3 = self.env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", delegator.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertEqual(av_del_3.delegated_out_votes, 10.0, "State 3: effective")
        out_after_state_3 = av_del_3.delegated_out_votes

        # State 4: Delegate absent (ineffective again)
        delegate.action_mark_absent()
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()
        av_del_4 = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(av_del_4.delegated_out_votes, 0.0, "State 4: ineffective")
        out_after_state_4 = av_del_4.delegated_out_votes

        # Same assembly.attendee.vote row is updated in place across states; use snapshots
        self.assertEqual(out_after_state_1, 0.0)
        self.assertEqual(out_after_state_2, 0.0)
        self.assertEqual(out_after_state_3, 10.0)
        self.assertEqual(out_after_state_4, 0.0)

    def test_batch_recomputation_consistency(self):
        """Batch recomputation produces same results as individual."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        attendee1 = assembly.attendee_ids[0]
        attendee2 = assembly.attendee_ids[1]

        # Give votes
        self._give_partner_votes(attendee1.partner_id, vote_type, 10)
        # pylint: disable=protected-access
        self._give_partner_votes(attendee2.partner_id, vote_type, 5)
        # pylint: disable=protected-access
        # Confirm both
        attendee1.action_confirm()
        attendee2.action_confirm()

        # Individual recomputation
        attendee1.recompute_attendee_vote_lines()
        attendee2.recompute_attendee_vote_lines()
        av1_individual = attendee1.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type
        )
        av2_individual = attendee2.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type
        )
        result_individual = (
            av1_individual.own_votes,
            av2_individual.own_votes,
        )  # noqa: F841

        # Batch recomputation
        (attendee1 | attendee2).recompute_attendee_vote_lines()
        av1_batch = attendee1.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type
        )
        av2_batch = attendee2.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type
        )
        result_batch = (av1_batch.own_votes, av2_batch.own_votes)  # noqa: F841

        # Results should be identical
        self.assertEqual(
            result_individual, result_batch, "Batch = individual recomputation"
        )

    def test_recompute_votes_core_qa_snapshot_stable_and_no_duplicate_rows(self):
        """QA for ``_recompute_votes_core`` phases: stable totals, no duplicate lines.

        After many full recomputes, persisted components and row cardinality must
        match the first pass (determinism + idempotence of the orchestrated flow).
        """
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 8)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type, 3)
        delegator.action_confirm()
        delegate.action_confirm()
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

        def snapshot_lines():
            lines = self.env["assembly.attendee.vote"].search(
                [("attendee_id", "in", assembly.attendee_ids.ids)],
                order="attendee_id asc, vote_type_id asc, id asc",
            )
            return tuple(
                (
                    line.attendee_id.id,
                    line.vote_type_id.id,
                    line.own_votes,
                    line.delegated_out_votes,
                    line.delegated_in_votes,
                    line.attendee_vote_total,
                )
                for line in lines
            )

        first = snapshot_lines()
        for _ in range(20):
            assembly.attendee_ids.recompute_attendee_vote_lines()
        last = snapshot_lines()
        self.assertEqual(first, last)

        Av = self.env["assembly.attendee.vote"]
        for att in assembly.attendee_ids:
            self.assertEqual(
                Av.search_count(
                    [
                        ("attendee_id", "=", att.id),
                        ("vote_type_id", "=", vote_type.id),
                    ]
                ),
                1,
                "Exactly one assembly.attendee.vote per (attendee, vote_type)",
            )


class TestRecomputeVotesPublicAPI(AssemblyTestMixin, TransactionCase):
    """Explicit QA on ``@api.model recompute_votes(attendees)`` (single batch entry point)."""

    @staticmethod
    def _snapshot_all_vote_lines(env, attendee_ids):
        lines = env["assembly.attendee.vote"].search(
            [("attendee_id", "in", list(attendee_ids))],
            order="attendee_id asc, vote_type_id asc, id asc",
        )
        return tuple(
            (
                line.attendee_id.id,
                line.vote_type_id.id,
                line.own_votes,
                line.delegated_out_votes,
                line.delegated_in_votes,
                line.attendee_vote_total,
            )
            for line in lines
        )

    def test_recompute_votes_twice_same_snapshot(self):
        """Two consecutive ``recompute_votes`` calls → same persisted snapshot."""
        Attendee = self.env["assembly.attendee"]
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        a0, a1 = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(a0.partner_id, vote_type, 2)
        self._give_partner_votes(a1.partner_id, vote_type, 3)
        a0.action_confirm()
        a1.action_confirm()
        Attendee.recompute_votes(assembly.attendee_ids)
        first = self._snapshot_all_vote_lines(self.env, assembly.attendee_ids.ids)
        Attendee.recompute_votes(assembly.attendee_ids)
        second = self._snapshot_all_vote_lines(self.env, assembly.attendee_ids.ids)
        self.assertEqual(first, second)

    def test_recompute_votes_after_unlink_all_lines_restores_snapshot(self):
        """Delete all ``assembly.attendee.vote`` rows and recompute → same snapshot."""
        Attendee = self.env["assembly.attendee"]
        Av = self.env["assembly.attendee.vote"]
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        a0, a1 = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(a0.partner_id, vote_type, 2)
        self._give_partner_votes(a1.partner_id, vote_type, 3)
        a0.action_confirm()
        a1.action_confirm()
        Attendee.recompute_votes(assembly.attendee_ids)
        expected = self._snapshot_all_vote_lines(self.env, assembly.attendee_ids.ids)
        Av.search([("attendee_id", "in", assembly.attendee_ids.ids)]).unlink()
        self.assertFalse(Av.search([("attendee_id", "in", assembly.attendee_ids.ids)]))
        Attendee.recompute_votes(assembly.attendee_ids)
        restored = self._snapshot_all_vote_lines(self.env, assembly.attendee_ids.ids)
        self.assertEqual(restored, expected)

    def test_recompute_votes_no_duplicate_rows_per_pair(self):
        """Several ``recompute_votes`` rounds: one row per (attendee, type)."""
        Attendee = self.env["assembly.attendee"]
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        for att in assembly.attendee_ids:
            self._give_partner_votes(att.partner_id, vote_type, 1)
            att.action_confirm()
        Av = self.env["assembly.attendee.vote"]
        for _ in range(5):
            Attendee.recompute_votes(assembly.attendee_ids)
        for att in assembly.attendee_ids:
            self.assertEqual(
                Av.search_count(
                    [
                        ("attendee_id", "=", att.id),
                        ("vote_type_id", "=", vote_type.id),
                    ]
                ),
                1,
            )

    def test_recompute_votes_order_independent_snapshot(self):
        """Input recordset order does not change the result."""
        Attendee = self.env["assembly.attendee"]
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        a0, a1 = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(a0.partner_id, vote_type, 5)
        self._give_partner_votes(a1.partner_id, vote_type, 6)
        a0.action_confirm()
        a1.action_confirm()
        d0, d1 = a0.id, a1.id
        Attendee.recompute_votes(Attendee.browse([d0, d1]))
        s_forward = self._snapshot_all_vote_lines(self.env, assembly.attendee_ids.ids)
        Attendee.recompute_votes(Attendee.browse([d1, d0]))
        s_reverse = self._snapshot_all_vote_lines(self.env, assembly.attendee_ids.ids)
        self.assertEqual(s_forward, s_reverse)

    def test_recompute_votes_empty_prefetch_delegator_no_partner_vote_stable(self):
        """Inbound delegators with no partner.vote rows: delegated_in is 0; double recompute stable."""
        Attendee = self.env["assembly.attendee"]
        partners = self._create_partners(self.env, 2, prefix="PvEmpty")
        assembly, _ = self._create_assembly_with_agenda(
            partner_domain="[('id', 'in', %s)]" % partners.ids,
        )
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator_att, delegate_att = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(delegate_att.partner_id, vote_type, 5)
        delegate_att.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator_att.partner_id.id,
                "delegate_partner_id": delegate_att.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        Attendee.recompute_votes(delegate_att)
        line = delegate_att.attendee_vote_ids.filtered(
            lambda av_line, vt=vote_type: av_line.vote_type_id == vt
        )
        self.assertEqual(len(line), 1)
        self.assertEqual(line.delegated_in_votes, 0.0)
        snap = self._snapshot_all_vote_lines(self.env, [delegate_att.id])
        Attendee.recompute_votes(delegate_att)
        self.assertEqual(
            self._snapshot_all_vote_lines(self.env, [delegate_att.id]), snap
        )

    def test_recompute_votes_non_attendee_delegator_idempotent(self):
        """Delegator without attendee row: ``recompute_votes`` twice is stable."""
        Attendee = self.env["assembly.attendee"]
        p_del = self.env["res.partner"].create(
            {"name": "StabDel", "is_company": False, "assembly_excluded": True}
        )
        p_def = self.env["res.partner"].create(
            {"name": "StabDef", "is_company": False, "assembly_excluded": False}
        )
        domain = "[('id', 'in', %s)]" % ([p_del.id, p_def.id],)
        assembly, _ = self._create_assembly_with_agenda(partner_domain=domain)
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        self._give_partner_votes(p_del, vote_type, 7)
        self._give_partner_votes(p_def, vote_type, 2)
        delegate_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_def)
        delegate_att.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_del.id,
                "delegate_partner_id": p_def.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        Attendee.recompute_votes(delegate_att)
        line1 = delegate_att.attendee_vote_ids.filtered(
            lambda r: r.vote_type_id == vote_type
        )
        tup1 = (
            line1.own_votes,
            line1.delegated_in_votes,
            line1.delegated_out_votes,
            line1.attendee_vote_total,
        )
        Attendee.recompute_votes(delegate_att)
        line2 = delegate_att.attendee_vote_ids.filtered(
            lambda r: r.vote_type_id == vote_type
        )
        tup2 = (
            line2.own_votes,
            line2.delegated_in_votes,
            line2.delegated_out_votes,
            line2.attendee_vote_total,
        )
        self.assertEqual(tup1, tup2)
        self.assertEqual(tup2[1], 7.0)

    def test_trigger_delegation_confirm_via_write_recomputes_totals(self):
        """``delegation.write`` (draft→confirmed) triggers ``recompute_votes`` via ORM."""
        Av = self.env["assembly.attendee.vote"]
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator, delegate = assembly.attendee_ids[0], assembly.attendee_ids[1]
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
                "delegation_state": "draft",
            }
        )
        line_d = Av.search(
            [
                ("attendee_id", "=", delegator.id),
                ("vote_type_id", "=", vote_type.id),
            ]
        )
        line_g = Av.search(
            [
                ("attendee_id", "=", delegate.id),
                ("vote_type_id", "=", vote_type.id),
            ]
        )
        self.assertEqual(len(line_d), 1)
        self.assertEqual(len(line_g), 1)
        self.assertEqual(line_d.delegated_out_votes, 0.0)
        self.assertEqual(line_g.delegated_in_votes, 0.0)
        delegation.write({"delegation_state": "confirmed"})
        line_d = Av.search(
            [
                ("attendee_id", "=", delegator.id),
                ("vote_type_id", "=", vote_type.id),
            ]
        )
        line_g = Av.search(
            [
                ("attendee_id", "=", delegate.id),
                ("vote_type_id", "=", vote_type.id),
            ]
        )
        self.assertEqual(len(line_d), 1)
        self.assertEqual(len(line_g), 1)
        self.assertEqual(line_d.delegated_out_votes, 10.0)
        self.assertEqual(line_g.delegated_in_votes, 10.0)

    def test_trigger_action_confirm_persists_vote_lines_without_manual_recompute(self):
        """``action_confirm`` must persist lines without calling ``recompute_votes`` in the test."""
        Av = self.env["assembly.attendee.vote"]
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vote_type, 4)
        att.action_confirm()
        lines = Av.search(
            [
                ("attendee_id", "=", att.id),
                ("vote_type_id", "=", vote_type.id),
            ]
        )
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.own_votes, 4.0)

    def test_trigger_action_mark_absent_recomputes_delegate_totals(self):
        """``action_mark_absent`` on delegator updates delegate ``delegated_in``."""
        Av = self.env["assembly.attendee.vote"]
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator, delegate = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 10)
        self._give_partner_votes(delegate.partner_id, vote_type, 3)
        delegator.action_confirm()
        delegate.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        line_g = Av.search(
            [
                ("attendee_id", "=", delegate.id),
                ("vote_type_id", "=", vote_type.id),
            ]
        )
        self.assertEqual(len(line_g), 1)
        self.assertEqual(line_g.delegated_in_votes, 10.0)
        delegator.action_mark_absent()
        line_g = Av.search(
            [
                ("attendee_id", "=", delegate.id),
                ("vote_type_id", "=", vote_type.id),
            ]
        )
        self.assertEqual(len(line_g), 1)
        self.assertEqual(line_g.delegated_in_votes, 0.0)

    def test_assembly_vote_type_write_auto_recomputes_attendee_vote_lines(self):
        """``assembly.write`` with ``vote_type_ids`` triggers ``recompute_votes`` on attendees."""
        Attendee = self.env["assembly.attendee"]
        Av = self.env["assembly.attendee.vote"].sudo()
        assembly, _ = self._create_assembly_with_agenda()
        vt1 = self._create_vote_type(self.env, name="Implicit VT1", code="IM1")
        vt2 = self._create_vote_type(self.env, name="Implicit VT2", code="IM2")
        assembly.assembly_type_id.write({"vote_type_ids": [(6, 0, [vt1.id, vt2.id])]})
        assembly.write({"vote_type_ids": [(6, 0, [vt1.id, vt2.id])]})
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vt1, 1)
        self._give_partner_votes(att.partner_id, vt2, 2)
        att.action_confirm()
        Attendee.recompute_votes(assembly.attendee_ids)
        self.assertEqual(Av.search_count([("attendee_id", "=", att.id)]), 2)
        assembly.write({"vote_type_ids": [(6, 0, [vt1.id])]})
        self.assertEqual(
            Av.search_count([("attendee_id", "=", att.id)]),
            1,
            "Removing a vote type from the assembly must drop obsolete rows on save",
        )
        self.assertFalse(
            Av.search(
                [
                    ("attendee_id", "=", att.id),
                    ("vote_type_id", "=", vt2.id),
                ]
            )
        )


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
                "delegation_state": "confirmed",
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
                "delegation_state": "draft",
            }
        )
        d_line_before = self._stored_vote_line(delegator, vote_type)
        self.assertEqual(d_line_before.delegated_out_votes, 0.0)
        assembly.delegation_ids.write({"delegation_state": "confirmed"})
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
                "delegation_state": "confirmed",
            }
        )
        d_line = self._stored_vote_line(delegator, vote_type)
        g_line = self._stored_vote_line(delegate, vote_type)
        self.assertEqual(d_line.delegated_out_votes, 3.0)
        self.assertEqual(g_line.delegated_in_votes, 3.0)
        del_rec.write({"delegation_state": "revoked"})
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
                "delegation_state": "confirmed",
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
        del_rec = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "draft",
            }
        )
        delegator.action_confirm()
        d_line = self._stored_vote_line(delegator, vote_type)
        self.assertEqual(d_line.delegated_out_votes, 0.0)
        delegate.action_confirm()
        del_rec.write({"delegation_state": "confirmed"})
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()
        d_line = self._stored_vote_line(delegator, vote_type)
        g_line = self._stored_vote_line(delegate, vote_type)
        self.assertEqual(d_line.delegated_out_votes, 5.0)
        self.assertEqual(g_line.delegated_in_votes, 5.0)


class TestRecomputationMultipleChanges(AssemblyTestMixin, TransactionCase):
    """Recomputation consistency across multiple simultaneous or sequential changes."""

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
