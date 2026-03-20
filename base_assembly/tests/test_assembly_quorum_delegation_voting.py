# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Tests for quorum, delegations, attendee.vote, votings and results.

Covers: Q1–Q11 (quorum), D1–D11 (delegations), V1–V11 (votings), R1–R5 (results).
See doc/VOTING_QUORUM_TEST_SCENARIOS.md.
"""

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestQuorumScenarios(AssemblyTestMixin, TransactionCase):
    """Q1–Q11: Quorum without/with attendees, delegations, state changes."""

    def test_Q1_quorum_without_attendees_confirmed(self):
        """Q1: No confirmed attendees → total_present=0, quorum_reached=False."""
        partners = self._create_partners(self.env, 4)
        assembly, _ = self._create_assembly_with_agenda(
            partner_domain="[('id', 'in', %s)]" % partners.ids
        )
        assembly.action_generate_attendees()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_possible_attendees, 4)
        self.assertEqual(assembly.total_present_attendees, 0)
        self.assertEqual(assembly.quorum_percentage, 0.0)
        self.assertFalse(assembly.quorum_reached)

    def test_Q2_quorum_with_present_attendees(self):
        """Q2: With present attendees → total_present and percentage correct."""
        partners = self._create_partners(self.env, 4)
        assembly, _ = self._create_assembly_with_agenda(
            partner_domain="[('id', 'in', %s)]" % partners.ids
        )
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        for att in assembly.attendee_ids[:2]:
            self._give_partner_votes(att.partner_id, vote_type, 1)
            att.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 2)
        self.assertEqual(assembly.quorum_percentage, 50.0)

    def test_Q3_quorum_percentage_reached(self):
        """Q3: Quorum by percentage reached."""
        partners = self._create_partners(self.env, 4)
        assembly, _ = self._create_assembly_with_agenda(
            partner_domain="[('id', 'in', %s)]" % partners.ids
        )
        assembly.quorum_value = 50.0
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        for att in assembly.attendee_ids[:2]:
            self._give_partner_votes(att.partner_id, vote_type, 1)
            att.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.invalidate_recordset()
        self.assertTrue(assembly.quorum_reached)

    def test_Q4_quorum_fixed_number_reached(self):
        """Q4: Quorum by fixed number."""
        partners = self._create_partners(self.env, 4)
        assembly, _ = self._create_assembly_with_agenda(
            partner_domain="[('id', 'in', %s)]" % partners.ids
        )
        assembly.quorum_type = "fixed"
        assembly.quorum_value = 2.0
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        for att in assembly.attendee_ids[:2]:
            self._give_partner_votes(att.partner_id, vote_type, 1)
            att.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.invalidate_recordset()
        self.assertTrue(assembly.quorum_reached)

    def test_Q5_quorum_second_call_any(self):
        """Q5: Second call type 'any' → one present is enough."""
        partners = self._create_partners(self.env, 4)
        assembly, _ = self._create_assembly_with_agenda(
            partner_domain="[('id', 'in', %s)]" % partners.ids
        )
        assembly.is_second_call = True
        assembly.quorum_second_call_type = "any"
        assembly.quorum_second_call_value = 0.0
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        self._give_partner_votes(assembly.attendee_ids[0].partner_id, vote_type, 1)
        assembly.attendee_ids[0].action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 1)
        self.assertTrue(assembly.quorum_reached)

    def test_Q6_quorum_with_active_delegation_delegate_confirmed(self):
        """Q6: Active delegation with delegate confirmed → delegator counts as present."""
        partners = self._create_partners(self.env, 4)
        assembly, _ = self._create_assembly_with_agenda(
            partner_domain="[('id', 'in', %s)]" % partners.ids
        )
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 1)
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
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
        delegator.recompute_votes()
        delegate.recompute_votes()
        assembly.invalidate_recordset()
        present = assembly.count_present_attendees()
        self.assertEqual(
            present, 2, "Delegator (represented by confirmed delegate) + delegate"
        )

    def test_Q7_delegation_invalid_for_present_delegate_not_confirmed(self):
        """Q7: Delegate not confirmed → delegator does not count as present."""
        partners = self._create_partners(self.env, 4)
        assembly, _ = self._create_assembly_with_agenda(
            partner_domain="[('id', 'in', %s)]" % partners.ids
        )
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 1)
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        delegator.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        delegator.recompute_votes()
        delegate.recompute_votes()
        assembly.invalidate_recordset()
        present = assembly.count_present_attendees()
        self.assertEqual(
            present,
            1,
            "Only delegator is confirmed; delegate not confirmed so delegator not represented",
        )

    def test_Q8_quorum_state_change_confirm_attendee(self):
        """Q8: Confirming attendee increases total_present."""
        partners = self._create_partners(self.env, 4)
        assembly, _ = self._create_assembly_with_agenda(
            partner_domain="[('id', 'in', %s)]" % partners.ids
        )
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 0)
        self._give_partner_votes(assembly.attendee_ids[0].partner_id, vote_type, 1)
        assembly.attendee_ids[0].action_confirm()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 1)
        self._give_partner_votes(assembly.attendee_ids[1].partner_id, vote_type, 1)
        assembly.attendee_ids[1].action_confirm()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 2)

    def test_Q9_quorum_state_change_mark_absent(self):
        """Q9: Marcar ausente disminuye total_present."""
        partners = self._create_partners(self.env, 4)
        assembly, _ = self._create_assembly_with_agenda(
            partner_domain="[('id', 'in', %s)]" % partners.ids
        )
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        for att in assembly.attendee_ids[:2]:
            self._give_partner_votes(att.partner_id, vote_type, 1)
            att.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 2)
        assembly.attendee_ids[1].action_mark_absent()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 1)

    def test_Q10_quorum_invalid_partner_domain_no_crash(self):
        """Q10: Invalid partner_domain → no crash."""
        assembly, _ = self._create_assembly_with_agenda(partner_domain="[('invalid")
        assembly.action_generate_attendees()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 0)
        self.assertFalse(assembly.quorum_reached)

    def test_Q11_quorum_empty_domain(self):
        """Q11: partner_domain that returns no partner → total_possible=0."""
        assembly, _ = self._create_assembly_with_agenda(
            partner_domain="[('id', '=', 0)]"
        )
        assembly.action_generate_attendees()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_possible_attendees, 0)
        self.assertFalse(assembly.quorum_reached)


class TestDelegationScenarios(AssemblyTestMixin, TransactionCase):
    """D1–D11: Total, partial, revoked, duplicate, circular delegation."""

    def test_D1_delegation_total_empty_vote_types(self):
        """D1: Total delegation (empty vote_type_ids) → delegate receives all types."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 5)
        self._give_partner_votes(delegate.partner_id, vote_type, 2)
        delegator.action_confirm()
        delegate.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(5, 0, 0)],
                "delegation_state": "confirmed",
            }
        )
        delegator.recompute_votes()
        delegate.recompute_votes()
        av_delegate = self.env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", delegate.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertEqual(av_delegate.delegated_in_votes, 5.0)
        self.assertEqual(av_delegate.attendee_vote_total, 2.0 + 5.0)

    def test_D2_delegation_partial_by_type(self):
        """D2: Partial delegation by type → only delegated type affects out/in."""
        vt1 = self._create_vote_type(self.env, "VT1")
        vt2 = self._create_vote_type(self.env, "VT2")
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Two types",
                "code": "TWO",
                "vote_type_ids": [(6, 0, (vt1 + vt2).ids)],
                "default_quorum_type": "percentage",
                "default_quorum_value": 50.0,
                "partner_domain": "[]",
            }
        )
        partners = self._create_partners(self.env, 3)
        assembly, _ = self._create_assembly_with_agenda(
            partner_domain="[('id', 'in', %s)]" % partners.ids,
            assembly_type=assembly_type,
        )
        assembly.action_generate_attendees()
        a, b = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(a.partner_id, vt1, 4)
        self._give_partner_votes(a.partner_id, vt2, 3)
        self._give_partner_votes(b.partner_id, vt1, 1)
        self._give_partner_votes(b.partner_id, vt2, 1)
        a.action_confirm()
        b.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(6, 0, vt1.ids)],
                "delegation_state": "confirmed",
            }
        )
        a.recompute_votes()
        b.recompute_votes()
        av_a_vt1 = self.env["assembly.attendee.vote"].search(
            [("attendee_id", "=", a.id), ("vote_type_id", "=", vt1.id)], limit=1
        )
        av_a_vt2 = self.env["assembly.attendee.vote"].search(
            [("attendee_id", "=", a.id), ("vote_type_id", "=", vt2.id)], limit=1
        )
        av_b_vt1 = self.env["assembly.attendee.vote"].search(
            [("attendee_id", "=", b.id), ("vote_type_id", "=", vt1.id)], limit=1
        )
        self.assertEqual(av_a_vt1.delegated_out_votes, 4.0)
        self.assertEqual(av_a_vt1.attendee_vote_total, 0.0)
        self.assertEqual(av_a_vt2.delegated_out_votes, 0.0)
        self.assertEqual(av_a_vt2.attendee_vote_total, 3.0)
        self.assertEqual(av_b_vt1.delegated_in_votes, 4.0)
        self.assertEqual(av_b_vt1.attendee_vote_total, 1.0 + 4.0)

    def test_D3_delegator_present_confirmed_delegation(self):
        """D3: Delegator present, delegation confirmed → out/in correct."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator, delegate = assembly.attendee_ids[0], assembly.attendee_ids[1]
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
        delegator.recompute_votes()
        delegate.recompute_votes()
        av_del = self.env["assembly.attendee.vote"].search(
            [("attendee_id", "=", delegator.id), ("vote_type_id", "=", vote_type.id)],
            limit=1,
        )
        av_dec = self.env["assembly.attendee.vote"].search(
            [("attendee_id", "=", delegate.id), ("vote_type_id", "=", vote_type.id)],
            limit=1,
        )
        self.assertEqual(av_del.attendee_vote_total, 0.0)
        self.assertEqual(av_dec.attendee_vote_total, 5.0)

    def test_D4_delegate_not_confirmed_then_confirm(self):
        """D4: Delegate not confirmed → on confirm, delegated_in applied."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator, delegate = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 3)
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        delegator.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        delegator.recompute_votes()
        delegate.recompute_votes()
        delegate.action_confirm()
        av = self.env["assembly.attendee.vote"].search(
            [("attendee_id", "=", delegate.id), ("vote_type_id", "=", vote_type.id)],
            limit=1,
        )
        self.assertEqual(av.delegated_in_votes, 3.0)
        self.assertEqual(av.attendee_vote_total, 1.0 + 3.0)

    def test_D5_duplicate_confirmed_delegation_same_type_raises(self):
        """D5: Two confirmed delegations same type → ValidationError."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        p1, p2, p3 = (
            assembly.attendee_ids[0].partner_id,
            assembly.attendee_ids[1].partner_id,
            assembly.attendee_ids[2].partner_id,
        )
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": p1.id,
                "delegate_partner_id": p2.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        with self.assertRaises(ValidationError) as ctx:
            self.env["assembly.delegation"].create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": p1.id,
                    "delegate_partner_id": p3.id,
                    "vote_type_ids": [(6, 0, vote_type.ids)],
                    "delegation_state": "confirmed",
                }
            )
        self.assertIn("already have a confirmed delegation", str(ctx.exception))

    def test_D6_revoked_delegation_reverts_votes(self):
        """D6: Revoke delegation → recompute restores own and removes in."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator, delegate = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 4)
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        delegator.action_confirm()
        delegate.action_confirm()
        d = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        delegator.recompute_votes()
        delegate.recompute_votes()
        av_dec = self.env["assembly.attendee.vote"].search(
            [("attendee_id", "=", delegate.id), ("vote_type_id", "=", vote_type.id)],
            limit=1,
        )
        self.assertEqual(av_dec.attendee_vote_total, 5.0)
        d.delegation_state = "revoked"
        delegator.recompute_votes()
        delegate.recompute_votes()
        av_del = self.env["assembly.attendee.vote"].search(
            [("attendee_id", "=", delegator.id), ("vote_type_id", "=", vote_type.id)],
            limit=1,
        )
        av_dec.invalidate_recordset()
        self.assertEqual(av_del.attendee_vote_total, 4.0)
        self.assertEqual(av_dec.attendee_vote_total, 1.0)

    def test_D7_circular_delegation_same_type(self):
        """D7: Circular A→B, B→A same type: model does not forbid; totals consistent."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        a, b = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(a.partner_id, vote_type, 2)
        self._give_partner_votes(b.partner_id, vote_type, 3)
        a.action_confirm()
        b.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": b.partner_id.id,
                "delegate_partner_id": a.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        a.recompute_votes()
        b.recompute_votes()
        av_a = self.env["assembly.attendee.vote"].search(
            [("attendee_id", "=", a.id), ("vote_type_id", "=", vote_type.id)], limit=1
        )
        av_b = self.env["assembly.attendee.vote"].search(
            [("attendee_id", "=", b.id), ("vote_type_id", "=", vote_type.id)], limit=1
        )
        self.assertEqual(av_a.attendee_vote_total + av_b.attendee_vote_total, 5.0)

    def test_D8_changes_after_confirmation_recompute(self):
        """D8: Confirm delegation after having confirmed attendees → recompute updates."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        a, b = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(a.partner_id, vote_type, 2)
        self._give_partner_votes(b.partner_id, vote_type, 1)
        a.action_confirm()
        b.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        a.recompute_votes()
        b.recompute_votes()
        av_b = self.env["assembly.attendee.vote"].search(
            [("attendee_id", "=", b.id), ("vote_type_id", "=", vote_type.id)], limit=1
        )
        self.assertEqual(av_b.attendee_vote_total, 3.0)

    def test_D9_delegator_equals_delegate_raises(self):
        """D9: Delegator = delegate → ValidationError."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        p = assembly.attendee_ids[0].partner_id
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        with self.assertRaises(ValidationError) as ctx:
            self.env["assembly.delegation"].create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": p.id,
                    "delegate_partner_id": p.id,
                    "vote_type_ids": [(6, 0, vote_type.ids)],
                }
            )
        self.assertIn("different", str(ctx.exception))

    def test_D10_delegate_outside_domain_raises(self):
        """D10: Delegate outside partner_domain → ValidationError."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        outside = self.env["res.partner"].create(
            {"name": "Outside", "is_company": False}
        )
        delegator = assembly.attendee_ids[0].partner_id
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        with self.assertRaises(ValidationError) as ctx:
            self.env["assembly.delegation"].create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": delegator.id,
                    "delegate_partner_id": outside.id,
                    "vote_type_ids": [(6, 0, vote_type.ids)],
                }
            )
        self.assertIn("convocable", str(ctx.exception).lower())

    def test_D11_two_delegations_same_delegator_different_types(self):
        """D11: Two delegations same delegator for different types → allowed."""
        vt1 = self._create_vote_type(self.env, "V1")
        vt2 = self._create_vote_type(self.env, "V2")
        at = self.env["assembly.type"].create(
            {
                "name": "Two",
                "code": "TWO",
                "vote_type_ids": [(6, 0, (vt1 + vt2).ids)],
                "default_quorum_type": "percentage",
                "default_quorum_value": 50.0,
                "partner_domain": "[]",
            }
        )
        partners = self._create_partners(self.env, 3)
        assembly, _ = self._create_assembly_with_agenda(
            partner_domain="[('id', 'in', %s)]" % partners.ids,
            assembly_type=at,
        )
        assembly.action_generate_attendees()
        a, b, c = (
            assembly.attendee_ids[0],
            assembly.attendee_ids[1],
            assembly.attendee_ids[2],
        )
        for att, v1, v2 in [(a, 2, 3), (b, 1, 1), (c, 1, 1)]:
            self._give_partner_votes(att.partner_id, vt1, v1)
            self._give_partner_votes(att.partner_id, vt2, v2)
            att.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(6, 0, vt1.ids)],
                "delegation_state": "confirmed",
            }
        )
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": c.partner_id.id,
                "vote_type_ids": [(6, 0, vt2.ids)],
                "delegation_state": "confirmed",
            }
        )
        a.recompute_votes()
        b.recompute_votes()
        c.recompute_votes()
        av_b_vt1 = self.env["assembly.attendee.vote"].search(
            [("attendee_id", "=", b.id), ("vote_type_id", "=", vt1.id)], limit=1
        )
        av_c_vt2 = self.env["assembly.attendee.vote"].search(
            [("attendee_id", "=", c.id), ("vote_type_id", "=", vt2.id)], limit=1
        )
        self.assertEqual(av_b_vt1.delegated_in_votes, 2.0)
        self.assertEqual(av_c_vt2.delegated_in_votes, 3.0)


class TestVotingScenarios(AssemblyTestMixin, TransactionCase):
    """V1–V11: Apertura, cierre, elegibilidad, doble voto, no emitidos."""

    def test_V1_voting_open_totals_possible(self):
        """V1: Open voting → total_votes_possible from confirmed attendees."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att1, att2 = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(att1.partner_id, vote_type, 3)
        self._give_partner_votes(att2.partner_id, vote_type, 2)
        att1.action_confirm()
        att2.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.assertEqual(voting.voting_state, "open")
        self.assertEqual(voting.total_votes_possible, 5.0)
        self.assertEqual(voting.total_votes_cast, 0.0)

    def test_V2_voting_close_creates_results(self):
        """V2: Cierre crea result_ids y agenda voted."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vote_type, 2)
        att.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att.id,
                "vote_option": "yes",
                "votes_applied": 2.0,
            }
        )
        voting.action_close()
        self.assertEqual(voting.voting_state, "closed")
        self.assertEqual(agenda.agenda_state, "voted")
        self.assertEqual(len(voting.result_ids), 5)

    def test_V3_only_confirmed_in_possible(self):
        """V3: Solo confirmados cuentan en total_votes_possible."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att1, att2 = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(att1.partner_id, vote_type, 2)
        self._give_partner_votes(att2.partner_id, vote_type, 3)
        att1.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.assertEqual(voting.total_votes_possible, 2.0)

    def test_V4_attendee_zero_votes_cannot_have_line(self):
        """V4: Attendee with 0 votes cannot have a line."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vote_type, 0)
        att.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        with self.assertRaises(ValidationError):
            self.env["assembly.voting.line"].create(
                {
                    "voting_id": voting.id,
                    "attendee_id": att.id,
                    "vote_option": "yes",
                    "votes_applied": 0.0,
                }
            )

    def test_V5_votes_applied_must_match_attendee_total(self):
        """V5: votes_applied debe igualar attendee_vote_total."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vote_type, 4)
        att.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        with self.assertRaises(ValidationError) as ctx:
            self.env["assembly.voting.line"].create(
                {
                    "voting_id": voting.id,
                    "attendee_id": att.id,
                    "vote_option": "yes",
                    "votes_applied": 2.0,
                }
            )
        self.assertIn("must match", str(ctx.exception))

    def test_V6_not_cast_in_results(self):
        """V6: No emitidos = possible - cast en resultados."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att1, att2 = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(att1.partner_id, vote_type, 3)
        self._give_partner_votes(att2.partner_id, vote_type, 2)
        att1.action_confirm()
        att2.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att1.id,
                "vote_option": "yes",
                "votes_applied": 3.0,
            }
        )
        voting.action_close()
        not_cast = voting.result_ids.filtered(lambda r: r.vote_option == "not_cast")
        self.assertEqual(not_cast.total_votes, 2.0)

    def test_V7_duplicate_vote_same_attendee_raises(self):
        """V7: Double vote same attendee → UNIQUE/ValidationError."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vote_type, 1)
        att.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att.id,
                "vote_option": "yes",
                "votes_applied": 1.0,
            }
        )
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.env["assembly.voting.line"].create(
                    {
                        "voting_id": voting.id,
                        "attendee_id": att.id,
                        "vote_option": "no",
                        "votes_applied": 1.0,
                    }
                )

    def test_V8_create_line_when_voting_closed_raises(self):
        """V8: Create line when voting closed → ValidationError."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vote_type, 1)
        att.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        voting.action_close()
        with self.assertRaises(ValidationError) as ctx:
            self.env["assembly.voting.line"].create(
                {
                    "voting_id": voting.id,
                    "attendee_id": att.id,
                    "vote_option": "yes",
                    "votes_applied": 1.0,
                }
            )
        self.assertIn("only be created when the voting is open", str(ctx.exception))

    def test_V9_close_already_closed_raises(self):
        """V9: Close voting already closed → UserError."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        voting.action_close()
        with self.assertRaises(UserError) as ctx:
            voting.action_close()
        self.assertIn("Only open votings", str(ctx.exception))

    def test_V10_participation_totals(self):
        """V10: total_votes_cast y participation correctos."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att1, att2 = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(att1.partner_id, vote_type, 5)
        self._give_partner_votes(att2.partner_id, vote_type, 3)
        att1.action_confirm()
        att2.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att1.id,
                "vote_option": "yes",
                "votes_applied": 5.0,
            }
        )
        self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att2.id,
                "vote_option": "no",
                "votes_applied": 3.0,
            }
        )
        voting.invalidate_recordset()
        self.assertEqual(voting.total_votes_cast, 8.0)
        self.assertEqual(voting.total_votes_possible, 8.0)
        self.assertEqual(voting.participation_percentage, 100.0)


class TestResultScenarios(AssemblyTestMixin, TransactionCase):
    """R1–R5: Aggregation, sum, percentages, not_cast."""

    def test_R1_aggregation_by_option(self):
        """R1: Correct aggregation by option."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att1, att2, att3 = (
            assembly.attendee_ids[0],
            assembly.attendee_ids[1],
            assembly.attendee_ids[2],
        )
        self._give_partner_votes(att1.partner_id, vote_type, 3)
        self._give_partner_votes(att2.partner_id, vote_type, 2)
        self._give_partner_votes(att3.partner_id, vote_type, 1)
        for att in (att1, att2, att3):
            att.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att1.id,
                "vote_option": "yes",
                "votes_applied": 3.0,
            }
        )
        self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att2.id,
                "vote_option": "yes",
                "votes_applied": 2.0,
            }
        )
        self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att3.id,
                "vote_option": "no",
                "votes_applied": 1.0,
            }
        )
        voting.action_close()
        yes_r = voting.result_ids.filtered(lambda r: r.vote_option == "yes")
        no_r = voting.result_ids.filtered(lambda r: r.vote_option == "no")
        self.assertEqual(yes_r.total_votes, 5.0)
        self.assertEqual(no_r.total_votes, 1.0)

    def test_R2_sum_results_equals_possible(self):
        """R2: Suma total_votes de result_ids = total posible."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vote_type, 4)
        att.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att.id,
                "vote_option": "yes",
                "votes_applied": 4.0,
            }
        )
        voting.action_close()
        total_result = sum(voting.result_ids.mapped("total_votes"))
        self.assertEqual(total_result, 4.0)
        self.assertEqual(voting.total_votes_possible, 4.0)

    def test_R3_result_percentages_coherent(self):
        """R3: Percentages sum to ~100%."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att1, att2 = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(att1.partner_id, vote_type, 2)
        self._give_partner_votes(att2.partner_id, vote_type, 3)
        att1.action_confirm()
        att2.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att1.id,
                "vote_option": "yes",
                "votes_applied": 2.0,
            }
        )
        self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att2.id,
                "vote_option": "no",
                "votes_applied": 3.0,
            }
        )
        voting.action_close()
        total_pct = sum(voting.result_ids.mapped("result_percentage"))
        self.assertAlmostEqual(total_pct, 100.0, places=1)

    def test_R4_not_cast_equals_possible_minus_cast(self):
        """R4: not_cast = possible - cast."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att1, att2 = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(att1.partner_id, vote_type, 2)
        self._give_partner_votes(att2.partner_id, vote_type, 3)
        att1.action_confirm()
        att2.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att1.id,
                "vote_option": "abstention",
                "votes_applied": 2.0,
            }
        )
        voting.action_close()
        not_cast = voting.result_ids.filtered(lambda r: r.vote_option == "not_cast")
        self.assertEqual(not_cast.total_votes, 3.0)
        self.assertEqual(
            voting.total_votes_possible - voting.total_votes_cast,
            not_cast.total_votes,
        )

    def test_R5_all_options_present(self):
        """R5: result_ids contiene yes, no, abstention, blank, not_cast."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vote_type, 1)
        att.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att.id,
                "vote_option": "blank",
                "votes_applied": 1.0,
            }
        )
        voting.action_close()
        options = set(voting.result_ids.mapped("vote_option"))
        self.assertEqual(
            options,
            {"yes", "no", "abstention", "blank", "not_cast"},
        )
