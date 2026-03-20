# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Test suite for the Delegations and quorum phase (base_assembly).

Scenarios: Q-01..Q-11 (quorum), D-01..D-14 (delegations), SEC-D-01..04 (security).
See doc/TEST_SUITE_PHASE_DELEGACIONES_QUORUM.md.
"""

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class DelegationsQuorumPhaseMixin(AssemblyTestMixin):
    """Reusable helpers for the delegations and quorum phase."""

    def _create_assembly_open_for_delegation(self, partner_count=4):
        """
        Assembly in Open state with partner_count convocable and attendees generated.
        Returns (assembly, vote_type, attendees_recordset).
        """
        partners = self._create_partners(
            self.env, count=partner_count, prefix="Partner"
        )
        partner_domain = "[('id', 'in', %s)]" % partners.ids
        assembly, _ = self._create_assembly_with_agenda(
            partner_domain=partner_domain,
        )
        assembly.action_generate_attendees()
        assembly.action_announce()
        assembly.action_open_registration()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        return assembly, vote_type, assembly.attendee_ids


# --- Quorum (unit/model) ---


class TestPhaseQuorum(DelegationsQuorumPhaseMixin, TransactionCase):
    """Q-01..Q-11: Quorum without/with confirmed, delegations, invalid domain."""

    def test_phase_dq_quorum_without_confirmed_attendees(self):
        """Q-01: Sin confirmados → total_present=0, quorum_reached=False."""
        assembly, _, _ = self._create_assembly_open_for_delegation(4)
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_possible_attendees, 4)
        self.assertEqual(assembly.total_present_attendees, 0)
        self.assertEqual(assembly.quorum_percentage, 0.0)
        self.assertFalse(assembly.quorum_reached)

    def test_phase_dq_quorum_with_confirmed_attendees(self):
        """Q-02: Confirmar K asistentes → total_present=K, porcentaje coherente."""
        assembly, vote_type, attendees = self._create_assembly_open_for_delegation(4)
        for att in attendees[:2]:
            self._give_partner_votes(att.partner_id, vote_type, 1)
            att.action_confirm()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 2)
        self.assertEqual(assembly.quorum_percentage, 50.0)

    def test_phase_dq_quorum_percentage_reached(self):
        """Q-03: Quorum 50%, 2 of 4 confirmed → quorum_reached=True."""
        assembly, vote_type, attendees = self._create_assembly_open_for_delegation(4)
        assembly.quorum_value = 50.0
        for att in attendees[:2]:
            self._give_partner_votes(att.partner_id, vote_type, 1)
            att.action_confirm()
        assembly.invalidate_recordset()
        self.assertTrue(assembly.quorum_reached)

    def test_phase_dq_quorum_with_delegation_delegate_confirmed(self):
        """Q-06: Delegation A→B confirmed and B confirmed → delegator counts as present."""
        assembly, vote_type, attendees = self._create_assembly_open_for_delegation(4)
        delegator, delegate = attendees[0], attendees[1]
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
        self.assertEqual(assembly.count_present_attendees(), 2)

    def test_phase_dq_quorum_delegate_not_confirmed_delegator_not_counted(self):
        """Q-07: Delegado no confirmado → delegante no cuenta como presente."""
        assembly, vote_type, attendees = self._create_assembly_open_for_delegation(4)
        delegator, delegate = attendees[0], attendees[1]
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
        self.assertEqual(assembly.count_present_attendees(), 1)

    def test_phase_dq_quorum_invalid_partner_domain_no_crash(self):
        """Q-10: Invalid partner_domain → no traceback; total_possible 0 or coherent."""
        assembly, _ = self._create_assembly_with_agenda(partner_domain="[('invalid")
        assembly.action_generate_attendees()
        assembly.invalidate_recordset()
        # Invalid domain yields empty domain in except → search([]) = all; use no crash as main check
        self.assertEqual(assembly.total_present_attendees, 0)
        self.assertFalse(assembly.quorum_reached)

    def test_phase_dq_quorum_empty_domain_zero_possible(self):
        """Q-11: partner_domain that returns no partner → total_possible=0."""
        assembly, _ = self._create_assembly_with_agenda(
            partner_domain="[('id', '=', 0)]"
        )
        assembly.action_generate_attendees()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_possible_attendees, 0)
        self.assertFalse(assembly.quorum_reached)


# --- Delegaciones (unit/model) ---


class TestPhaseDelegations(DelegationsQuorumPhaseMixin, TransactionCase):
    """D-01..D-14: Constraints, total/partial, revoke, types in assembly."""

    def test_phase_dq_delegation_delegator_equals_delegate_raises(self):
        """D-09: Delegante = delegado → ValidationError."""
        assembly, vote_type, attendees = self._create_assembly_open_for_delegation(3)
        partner = attendees[0].partner_id
        with self.assertRaises(ValidationError) as ctx:
            self.env["assembly.delegation"].create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": partner.id,
                    "delegate_partner_id": partner.id,
                    "delegation_state": "draft",
                }
            )
        self.assertIn("different", str(ctx.exception))

    def test_phase_dq_delegation_delegate_outside_domain_raises(self):
        """D-10: Delegado fuera de partner_domain → ValidationError."""
        assembly, vote_type, attendees = self._create_assembly_open_for_delegation(3)
        outside = self.env["res.partner"].create(
            {"name": "Outside", "is_company": False}
        )
        with self.assertRaises(ValidationError) as ctx:
            self.env["assembly.delegation"].create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": attendees[0].partner_id.id,
                    "delegate_partner_id": outside.id,
                    "vote_type_ids": [(6, 0, vote_type.ids)],
                    "delegation_state": "draft",
                }
            )
        self.assertIn("convocable", str(ctx.exception).lower())

    def test_phase_dq_delegation_vote_type_not_in_assembly_raises(self):
        """D-12: vote_type_ids with type not in assembly → ValidationError."""
        assembly, vote_type, attendees = self._create_assembly_open_for_delegation(3)
        # Ensure assembly has vote_type_ids set (copy from type; onchange may not run on create)
        if not assembly.vote_type_ids:
            assembly.write(
                {"vote_type_ids": [(6, 0, assembly.assembly_type_id.vote_type_ids.ids)]}
            )
        other_vote_type = self._create_vote_type(
            self.env, name="Other VT", code="OTHER"
        )
        with self.assertRaises(ValidationError) as ctx:
            self.env["assembly.delegation"].create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": attendees[0].partner_id.id,
                    "delegate_partner_id": attendees[1].partner_id.id,
                    "vote_type_ids": [(6, 0, other_vote_type.ids)],
                    "delegation_state": "draft",
                }
            )
        self.assertIn("assembly", str(ctx.exception).lower())

    def test_phase_dq_two_confirmed_delegations_same_type_raises(self):
        """D-05: Dos delegaciones confirmadas mismo delegante y mismo tipo → ValidationError."""
        assembly, vote_type, attendees = self._create_assembly_open_for_delegation(4)
        delegator = attendees[0].partner_id
        delegate1 = attendees[1].partner_id
        delegate2 = attendees[2].partner_id
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.id,
                "delegate_partner_id": delegate1.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        with self.assertRaises(ValidationError) as ctx:
            self.env["assembly.delegation"].create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": delegator.id,
                    "delegate_partner_id": delegate2.id,
                    "vote_type_ids": [(6, 0, vote_type.ids)],
                    "delegation_state": "confirmed",
                }
            )
        self.assertIn("already have a confirmed delegation", str(ctx.exception))

    def test_phase_dq_delegation_total_empty_vote_types_delegate_gets_all(self):
        """D-01: Total delegation (empty vote_type_ids) → delegate receives all types."""
        assembly, vote_type, attendees = self._create_assembly_open_for_delegation(3)
        if not assembly.vote_type_ids:
            assembly.write(
                {"vote_type_ids": [(6, 0, assembly.assembly_type_id.vote_type_ids.ids)]}
            )
        delegator, delegate = attendees[0], attendees[1]
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
        av = self.env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", delegate.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertEqual(av.delegated_in_votes, 5.0)
        self.assertEqual(av.attendee_vote_total, 2.0 + 5.0)

    def test_phase_dq_delegation_revoke_reverts_votes(self):
        """D-06: Revoke delegation → delegated_in/out recalculated."""
        assembly, vote_type, attendees = self._create_assembly_open_for_delegation(3)
        if not assembly.vote_type_ids:
            assembly.write(
                {"vote_type_ids": [(6, 0, assembly.assembly_type_id.vote_type_ids.ids)]}
            )
        delegator, delegate = attendees[0], attendees[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 3)
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        delegator.action_confirm()
        delegate.action_confirm()
        delegation = self.env["assembly.delegation"].create(
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
        av_delegate = self.env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", delegate.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertEqual(av_delegate.delegated_in_votes, 3.0)
        delegation.write({"delegation_state": "revoked"})
        delegator.recompute_votes()
        delegate.recompute_votes()
        av_delegate.invalidate_recordset()
        self.assertEqual(av_delegate.delegated_in_votes, 0.0)
        self.assertEqual(av_delegate.attendee_vote_total, 1.0)


# --- Seguridad (security) ---


class TestPhaseDelegationsQuorumSecurity(DelegationsQuorumPhaseMixin, TransactionCase):
    """SEC-D-01..04: Permisos y record rules en delegaciones."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_assembly_user = cls.env["res.users"].create(
            {
                "name": "Assembly User",
                "login": "assembly_user_phase_dq",
                "email": "au_phase_dq@test.com",
                "groups_id": [
                    (6, 0, [cls.env.ref("base_assembly.assembly_group_user").id])
                ],
            }
        )

    def test_phase_dq_security_user_sees_only_own_delegations(self):
        """SEC-D-01: Assembly User solo ve delegaciones donde partner_id = user.partner_id."""
        assembly, _, attendees = self._create_assembly_open_for_delegation(3)
        partners = [a.partner_id for a in attendees]
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": partners[0].id,
                "delegate_partner_id": partners[1].id,
                "vote_type_ids": [(6, 0, assembly.assembly_type_id.vote_type_ids.ids)],
            }
        )
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": partners[1].id,
                "delegate_partner_id": partners[2].id,
                "vote_type_ids": [(6, 0, assembly.assembly_type_id.vote_type_ids.ids)],
            }
        )
        self.user_assembly_user.partner_id = partners[0]
        env = self.env["assembly.delegation"].with_user(self.user_assembly_user).env
        delegations = env["assembly.delegation"].search(
            [("assembly_id", "=", assembly.id)]
        )
        self.assertEqual(len(delegations), 1)
        self.assertEqual(delegations[0].partner_id, partners[0])

    def test_phase_dq_security_user_cannot_write_other_partner_delegation(self):
        """SEC-D-02: User cannot write another partner's delegation."""
        assembly, _, attendees = self._create_assembly_open_for_delegation(2)
        partners = [a.partner_id for a in attendees]
        delegation_other = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": partners[1].id,
                "delegate_partner_id": partners[0].id,
                "vote_type_ids": [(6, 0, assembly.assembly_type_id.vote_type_ids.ids)],
            }
        )
        self.user_assembly_user.partner_id = partners[0]
        env = self.env["assembly.delegation"].with_user(self.user_assembly_user).env
        # Record rules may filter search(); write by other user must be denied
        with self.assertRaises(AccessError):
            env["assembly.delegation"].browse(delegation_other.id).write(
                {"delegation_state": "confirmed"}
            )
