# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Production-grade tests for vote recomputation consistency.

Tests that vote recomputation is:
- Deterministic (same inputs → same outputs)
- Idempotent (multiple calls = same result)
- Complete (all vote types, all attendees)
- Consistent across all scenarios
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
    """QA explícita sobre ``@api.model recompute_votes(attendees)`` (única entrada batch)."""

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
        """Dos llamadas seguidas a ``recompute_votes`` → mismo estado persistido."""
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
        """Borrar todas las filas ``assembly.attendee.vote`` y recomputar → mismo snapshot."""
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
        """Varias rondas de ``recompute_votes``: una fila por (asistente, tipo)."""
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
        """El orden del recordset de entrada no altera el resultado."""
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

    def test_recompute_votes_non_attendee_delegator_idempotent(self):
        """Delegador sin fila de asistente: ``recompute_votes`` dos veces estable."""
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
        """``delegation.write`` (draft→confirmed) dispara ``recompute_votes`` vía ORM."""
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
        """``action_confirm`` debe persistir líneas sin llamar a ``recompute_votes`` en el test."""
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
        """``action_mark_absent`` en delegador actualiza ``delegated_in`` del delegado."""
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
        """``assembly.write`` con ``vote_type_ids`` dispara ``recompute_votes`` en asistentes."""
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
            "Quitar un tipo en la asamblea debe limpiar filas obsoletas al guardar",
        )
        self.assertFalse(
            Av.search(
                [
                    ("attendee_id", "=", att.id),
                    ("vote_type_id", "=", vt2.id),
                ]
            )
        )
