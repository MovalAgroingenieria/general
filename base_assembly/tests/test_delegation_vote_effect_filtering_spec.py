# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Delegations affect votes when saved and the delegate is a confirmed attendee."""

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestDelegationVoteEffectFilteringSpec(AssemblyTestMixin, TransactionCase):
    """Spec: saved delegation + confirmed delegate attendee changes vote lines."""

    @staticmethod
    def _line(attendee, vote_type):
        return attendee.env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", attendee.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )

    def test_spec_confirmed_delegation_and_delegate_confirmed_has_effect(self):
        """(1) Saved delegation + confirmed delegate → out/in persisted."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        delegator, delegate = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vt, 6)
        self._give_partner_votes(delegate.partner_id, vt, 2)
        delegator.action_confirm()
        delegate.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vt.ids)],
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        self.assertEqual(self._line(delegator, vt).delegated_out_votes, 6.0)
        self.assertEqual(self._line(delegate, vt).delegated_in_votes, 6.0)
        self.assertEqual(self._line(delegate, vt).attendee_vote_total, 8.0)

    def test_saved_delegation_without_confirmed_delegate_has_no_vote_effect(self):
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        delegator, delegate = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vt, 5)
        self._give_partner_votes(delegate.partner_id, vt, 3)
        delegator.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vt.ids)],
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        self.assertEqual(self._line(delegator, vt).delegated_out_votes, 0.0)
        self.assertEqual(self._line(delegate, vt).delegated_in_votes, 0.0)

    def test_unlink_delegation_clears_vote_effect(self):
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        a, b = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(a.partner_id, vt, 4)
        self._give_partner_votes(b.partner_id, vt, 1)
        (a | b).action_confirm()
        d_rec = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(6, 0, vt.ids)],
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        self.assertEqual(self._line(a, vt).delegated_out_votes, 4.0)
        self.assertEqual(self._line(b, vt).delegated_in_votes, 4.0)
        d_rec.unlink()
        assembly.attendee_ids.recompute_attendee_vote_lines()
        self.assertEqual(self._line(a, vt).delegated_out_votes, 0.0)
        self.assertEqual(self._line(b, vt).delegated_in_votes, 0.0)
        self.assertEqual(self._line(b, vt).attendee_vote_total, 1.0)

    def test_spec_delegated_in_not_redelegated_chain_blocked(self):
        """(4) Chaining blocked: delegate cannot re-delegate the same vote types."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        p0, p1, p2 = (
            assembly.attendee_ids[0],
            assembly.attendee_ids[1],
            assembly.attendee_ids[2],
        )
        for att in (p0, p1, p2):
            self._give_partner_votes(att.partner_id, vt, 2)
        (p0 | p1 | p2).action_confirm()
        Delegation = self.env["assembly.delegation"]
        Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": p0.partner_id.id,
                "delegate_partner_id": p1.partner_id.id,
                "vote_type_ids": [(6, 0, vt.ids)],
            }
        )
        with self.assertRaises(ValidationError):
            Delegation.create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": p1.partner_id.id,
                    "delegate_partner_id": p2.partner_id.id,
                    "vote_type_ids": [(6, 0, vt.ids)],
                }
            )

    def test_partner_layer_excludes_delegate_not_confirmed_attendee(self):
        Delegation = self.env["assembly.delegation"]
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        a, b = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(a.partner_id, vt, 1)
        self._give_partner_votes(b.partner_id, vt, 1)
        a.action_confirm()
        shell = Delegation.new(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id,
                "delegate_partner_id": b.partner_id,
                "vote_type_ids": [(6, 0, vt.ids)],
            }
        )
        eff = Delegation._get_effective_delegations(delegations=shell)
        self.assertFalse(eff)
        self.assertFalse(Delegation._apply_vote_effect_partner_filters(shell))

    def test_spec_partial_vote_type_ids_only_affect_listed_types(self):
        """Non-empty ``vote_type_ids`` ⇒ effect only on those types (others unchanged)."""
        env = self.env
        vt1 = self._create_vote_type(env, name="SpecPart A")
        vt2 = self._create_vote_type(env, name="SpecPart B")
        atype = self._create_assembly_type(env, name="SpecPart AT", vote_type=vt1)
        atype.write({"vote_type_ids": [(4, vt2.id)]})
        partners = self._create_partners(env, 3, prefix="SpecPart")
        assembly, _ = self._create_assembly_with_agenda(
            assembly_type=atype,
            partner_domain="[('id', 'in', %s)]" % (partners.ids,),
        )
        assembly.vote_type_ids = [(6, 0, [vt1.id, vt2.id])]
        assembly.action_generate_attendees()
        delegator, delegate = assembly.attendee_ids[0], assembly.attendee_ids[1]
        for vt in (vt1, vt2):
            self._give_partner_votes(delegator.partner_id, vt, 3)
            self._give_partner_votes(delegate.partner_id, vt, 1)
        delegator.action_confirm()
        delegate.action_confirm()
        env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, [vt1.id])],
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        self.assertEqual(self._line(delegator, vt1).delegated_out_votes, 3.0)
        self.assertEqual(self._line(delegator, vt2).delegated_out_votes, 0.0)
        self.assertEqual(self._line(delegate, vt1).delegated_in_votes, 3.0)
        self.assertEqual(self._line(delegate, vt2).delegated_in_votes, 0.0)

    def test_spec_empty_vote_type_ids_covers_all_assembly_vote_types(self):
        """Empty ``vote_type_ids`` ⇒ full delegation over all assembly vote types."""
        env = self.env
        vt1 = self._create_vote_type(env, name="SpecAll A")
        vt2 = self._create_vote_type(env, name="SpecAll B")
        atype = self._create_assembly_type(env, name="SpecAll AT", vote_type=vt1)
        atype.write({"vote_type_ids": [(4, vt2.id)]})
        partners = self._create_partners(env, 3, prefix="SpecAll")
        assembly, _ = self._create_assembly_with_agenda(
            assembly_type=atype,
            partner_domain="[('id', 'in', %s)]" % (partners.ids,),
        )
        assembly.vote_type_ids = [(6, 0, [vt1.id, vt2.id])]
        assembly.action_generate_attendees()
        delegator, delegate = assembly.attendee_ids[0], assembly.attendee_ids[1]
        for vt in (vt1, vt2):
            self._give_partner_votes(delegator.partner_id, vt, 2)
            self._give_partner_votes(delegate.partner_id, vt, 1)
        delegator.action_confirm()
        delegate.action_confirm()
        env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, [])],
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        self.assertEqual(self._line(delegator, vt1).delegated_out_votes, 2.0)
        self.assertEqual(self._line(delegator, vt2).delegated_out_votes, 2.0)
        self.assertEqual(self._line(delegate, vt1).delegated_in_votes, 2.0)
        self.assertEqual(self._line(delegate, vt2).delegated_in_votes, 2.0)

    def test_spec_delegation_covers_vote_type_matches_expansion(self):
        """Single per-type coverage API aligned with ``_get_effective_delegations``."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        a0, a1 = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(a0.partner_id, vt, 1)
        self._give_partner_votes(a1.partner_id, vt, 1)
        (a0 | a1).action_confirm()
        d = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": a0.partner_id.id,
                "delegate_partner_id": a1.partner_id.id,
                "vote_type_ids": [(6, 0, vt.ids)],
            }
        )
        self.assertTrue(d.delegation_covers_vote_type(vt))
        self.assertFalse(
            d.delegation_covers_vote_type(
                self._create_vote_type(self.env, name="SpecOther VT")
            )
        )
