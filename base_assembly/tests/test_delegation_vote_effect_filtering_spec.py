# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Single filter for delegations that affect votes (confirmed + delegate confirmed)."""

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestDelegationVoteEffectFilteringSpec(AssemblyTestMixin, TransactionCase):
    """Spec: only confirmed delegation + confirmed delegate attendee changes vote lines."""

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
        """(1) Confirmada + delegado confirmado → out/in persistidos."""
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
                "delegation_state": "confirmed",
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        self.assertEqual(self._line(delegator, vt).delegated_out_votes, 6.0)
        self.assertEqual(self._line(delegate, vt).delegated_in_votes, 6.0)
        self.assertEqual(self._line(delegate, vt).attendee_vote_total, 8.0)

    def test_spec_confirmed_row_but_delegate_not_confirmed_no_vote_effect(self):
        """(2)(3) Estado BD incoherente: confirmada sin delegado confirmado → sin efecto.

        The ORM blocks normal confirmation; SQL simulates a bad import.
        """
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        delegator, delegate = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vt, 5)
        self._give_partner_votes(delegate.partner_id, vt, 3)
        delegator.action_confirm()
        del_rec = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vt.ids)],
                "delegation_state": "draft",
            }
        )
        self.env.cr.execute(
            "UPDATE assembly_delegation SET delegation_state = %s WHERE id = %s",
            ("confirmed", del_rec.id),
        )
        del_rec.invalidate_recordset()
        assembly.attendee_ids.recompute_attendee_vote_lines()
        self.assertEqual(self._line(delegator, vt).delegated_out_votes, 0.0)
        self.assertEqual(self._line(delegator, vt).attendee_vote_total, 5.0)
        self.assertEqual(self._line(delegate, vt).delegated_in_votes, 0.0)

    def test_spec_draft_and_revoked_no_vote_effect(self):
        """(3) Draft or revoked do not change persisted totals."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        a, b = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(a.partner_id, vt, 4)
        self._give_partner_votes(b.partner_id, vt, 1)
        (a | b).action_confirm()
        d_draft = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(6, 0, vt.ids)],
                "delegation_state": "draft",
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        self.assertEqual(self._line(a, vt).delegated_out_votes, 0.0)
        self.assertEqual(self._line(b, vt).delegated_in_votes, 0.0)
        d_draft.write({"delegation_state": "confirmed"})
        assembly.attendee_ids.recompute_attendee_vote_lines()
        self.assertEqual(self._line(a, vt).delegated_out_votes, 4.0)
        d_draft.write({"delegation_state": "revoked"})
        assembly.attendee_ids.recompute_attendee_vote_lines()
        self.assertEqual(self._line(a, vt).delegated_out_votes, 0.0)
        self.assertEqual(self._line(b, vt).delegated_in_votes, 0.0)
        self.assertEqual(self._line(b, vt).attendee_vote_total, 1.0)

    def test_spec_delegated_in_not_redelegated_chain_blocked(self):
        """(4) No se puede encadenar: quien recibe no delega los mismos tipos."""
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
                "delegation_state": "confirmed",
            }
        )
        with self.assertRaises(ValidationError):
            Delegation.create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": p1.partner_id.id,
                    "delegate_partner_id": p2.partner_id.id,
                    "vote_type_ids": [(6, 0, vt.ids)],
                    "delegation_state": "confirmed",
                }
            )

    def test_spec_filter_helper_excludes_non_effective(self):
        """Partner layer: draft / unconfirmed delegate → empty ``_get_effective_delegations(delegations=)``."""
        Delegation = self.env["assembly.delegation"]
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        a, b = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(a.partner_id, vt, 1)
        self._give_partner_votes(b.partner_id, vt, 1)
        a.action_confirm()
        d1 = Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(6, 0, vt.ids)],
                "delegation_state": "draft",
            }
        )
        eff = Delegation._get_effective_delegations(delegations=d1)
        self.assertFalse(eff)
        self.assertFalse(Delegation._apply_vote_effect_partner_filters(d1))

    def test_spec_partial_vote_type_ids_only_affect_listed_types(self):
        """Non-empty ``vote_type_ids`` ⇒ efecto solo en esos tipos (resto sin out/in)."""
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
                "delegation_state": "confirmed",
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
                "delegation_state": "confirmed",
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
        d = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": assembly.attendee_ids[0].partner_id.id,
                "delegate_partner_id": assembly.attendee_ids[1].partner_id.id,
                "vote_type_ids": [(6, 0, vt.ids)],
                "delegation_state": "draft",
            }
        )
        self.assertTrue(d.delegation_covers_vote_type(vt))
        self.assertFalse(
            d.delegation_covers_vote_type(
                self._create_vote_type(self.env, name="SpecOther VT")
            )
        )
