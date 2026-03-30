# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Overlap validation: effective types; draft/revoked do not block."""

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestDelegationOverlapValidationSpec(AssemblyTestMixin, TransactionCase):
    """Reglas 1–4: solape en tipos expandidos; solo confirmadas compiten."""

    def _assembly_three_attendees_two_vote_types(self):
        env = self.env
        vt1 = self._create_vote_type(env, name="Overlap VT1")
        vt2 = self._create_vote_type(env, name="Overlap VT2")
        atype = self._create_assembly_type(env, name="Overlap type", vote_type=vt1)
        atype.write({"vote_type_ids": [(4, vt2.id)]})
        partners = self._create_partners(env, 3)
        assembly, _ = self._create_assembly_with_agenda(
            assembly_type=atype,
            partner_domain="[('id', 'in', %s)]" % partners.ids,
        )
        assembly.vote_type_ids = [(6, 0, [vt1.id, vt2.id])]
        assembly.action_generate_attendees()
        return assembly, vt1, vt2

    def test_reject_two_confirmed_overlapping_same_vote_type(self):
        """(1) Two confirmed delegations for same delegator overlapping on one type → error."""
        Delegation = self.env["assembly.delegation"]
        assembly, vt1, _vt2 = self._assembly_three_attendees_two_vote_types()
        a, b, c = (
            assembly.attendee_ids[0],
            assembly.attendee_ids[1],
            assembly.attendee_ids[2],
        )
        (a | b | c).action_confirm()
        Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(6, 0, [vt1.id])],
                "delegation_state": "confirmed",
            }
        )
        with self.assertRaises(ValidationError) as ex:
            Delegation.create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": a.partner_id.id,
                    "delegate_partner_id": c.partner_id.id,
                    "vote_type_ids": [(6, 0, [vt1.id])],
                    "delegation_state": "confirmed",
                }
            )
        self.assertIn("vote type", str(ex.exception).lower())

    def test_full_delegation_covers_all_types_blocks_partial_overlap(self):
        """(2)(3) Full delegation (empty M2M) overlaps any assembly vote type."""
        Delegation = self.env["assembly.delegation"]
        assembly, vt1, _vt2 = self._assembly_three_attendees_two_vote_types()
        a, b, c = (
            assembly.attendee_ids[0],
            assembly.attendee_ids[1],
            assembly.attendee_ids[2],
        )
        (a | b | c).action_confirm()
        Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(5, 0, 0)],
                "delegation_state": "confirmed",
            }
        )
        with self.assertRaises(ValidationError):
            Delegation.create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": a.partner_id.id,
                    "delegate_partner_id": c.partner_id.id,
                    "vote_type_ids": [(6, 0, [_vt2.id])],
                    "delegation_state": "confirmed",
                }
            )

    def test_disjoint_partial_delegations_allowed(self):
        """(4) A→B solo vt1 y A→C solo vt2: ambas confirmadas permitidas."""
        Delegation = self.env["assembly.delegation"]
        assembly, vt1, vt2 = self._assembly_three_attendees_two_vote_types()
        a, b, c = (
            assembly.attendee_ids[0],
            assembly.attendee_ids[1],
            assembly.attendee_ids[2],
        )
        (a | b | c).action_confirm()
        Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(6, 0, [vt1.id])],
                "delegation_state": "confirmed",
            }
        )
        d2 = Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": c.partner_id.id,
                "vote_type_ids": [(6, 0, [vt2.id])],
                "delegation_state": "confirmed",
            }
        )
        self.assertTrue(d2)

    def test_confirm_draft_delegation_overlaps_existing_confirmed_rejected(self):
        """Draft→confirm cannot overlap another confirmed delegation for the same delegator."""
        Delegation = self.env["assembly.delegation"]
        assembly, vt1, _vt2 = self._assembly_three_attendees_two_vote_types()
        a, b, c = (
            assembly.attendee_ids[0],
            assembly.attendee_ids[1],
            assembly.attendee_ids[2],
        )
        (a | b | c).action_confirm()
        Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(6, 0, [vt1.id])],
                "delegation_state": "confirmed",
            }
        )
        d_draft = Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": c.partner_id.id,
                "vote_type_ids": [(6, 0, [vt1.id])],
                "delegation_state": "draft",
            }
        )
        with self.assertRaises(ValidationError):
            d_draft.write({"delegation_state": "confirmed"})

    def test_draft_sibling_does_not_block_confirmed_same_vote_types(self):
        """(4) Borrador no cuenta: segunda confirmada misma cobertura permitida."""
        Delegation = self.env["assembly.delegation"]
        assembly, vt1, _vt2 = self._assembly_three_attendees_two_vote_types()
        a, b, c = (
            assembly.attendee_ids[0],
            assembly.attendee_ids[1],
            assembly.attendee_ids[2],
        )
        (a | b | c).action_confirm()
        Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(6, 0, [vt1.id])],
                "delegation_state": "draft",
            }
        )
        d2 = Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": c.partner_id.id,
                "vote_type_ids": [(6, 0, [vt1.id])],
                "delegation_state": "confirmed",
            }
        )
        self.assertTrue(d2)

    def test_revoked_sibling_does_not_block_confirmed_same_vote_types(self):
        """(4) Revocada no cuenta: nueva confirmada misma cobertura permitida."""
        Delegation = self.env["assembly.delegation"]
        assembly, vt1, _vt2 = self._assembly_three_attendees_two_vote_types()
        a, b, c = (
            assembly.attendee_ids[0],
            assembly.attendee_ids[1],
            assembly.attendee_ids[2],
        )
        (a | b | c).action_confirm()
        d1 = Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(6, 0, [vt1.id])],
                "delegation_state": "confirmed",
            }
        )
        d1.write({"delegation_state": "revoked"})
        d2 = Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": c.partner_id.id,
                "vote_type_ids": [(6, 0, [vt1.id])],
                "delegation_state": "confirmed",
            }
        )
        self.assertTrue(d2)

    def test_intersect_effective_vote_types_matches_expanded_coverage(self):
        """Symmetric intersection on expanded sets (empty M2M = all types)."""
        Delegation = self.env["assembly.delegation"]
        assembly, vt1, vt2 = self._assembly_three_attendees_two_vote_types()
        a, b = assembly.attendee_ids[0], assembly.attendee_ids[1]
        (a | b).action_confirm()
        d = Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(5, 0, 0)],
                "delegation_state": "draft",
            }
        )
        eff_partial = Delegation._delegation_effective_vote_types(
            assembly, self.env["vote.type"].browse([vt2.id])
        )
        overlap = Delegation._delegation_intersect_effective_vote_types(
            eff_partial, d._get_effective_vote_types()
        )
        self.assertEqual(set(overlap.ids), {vt2.id})

    def test_intersect_effective_vote_types_empty_when_disjoint(self):
        """No overlap ⇒ empty intersection (validation does not fire for disjoint types)."""
        Delegation = self.env["assembly.delegation"]
        assembly, vt1, vt2 = self._assembly_three_attendees_two_vote_types()
        a = Delegation._delegation_effective_vote_types(
            assembly, self.env["vote.type"].browse([vt1.id])
        )
        b = Delegation._delegation_effective_vote_types(
            assembly, self.env["vote.type"].browse([vt2.id])
        )
        inter = Delegation._delegation_intersect_effective_vote_types(a, b)
        self.assertFalse(inter)

    def test_write_confirmed_to_overlap_vote_types_rejected(self):
        """Editing M2M on a confirmed delegation to overlap another confirmed for same delegator → error."""
        Delegation = self.env["assembly.delegation"]
        assembly, vt1, vt2 = self._assembly_three_attendees_two_vote_types()
        a, b, c = (
            assembly.attendee_ids[0],
            assembly.attendee_ids[1],
            assembly.attendee_ids[2],
        )
        (a | b | c).action_confirm()
        d1 = Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(6, 0, [vt1.id])],
                "delegation_state": "confirmed",
            }
        )
        d2 = Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": c.partner_id.id,
                "vote_type_ids": [(6, 0, [vt2.id])],
                "delegation_state": "confirmed",
            }
        )
        with self.assertRaises(ValidationError):
            d2.write({"vote_type_ids": [(6, 0, [vt1.id, vt2.id])]})
        self.assertTrue(d1 and d2)

    def test_reject_vote_type_not_in_assembly_vote_types(self):
        """``vote_type_ids`` must only reference types allowed on the assembly."""
        Delegation = self.env["assembly.delegation"]
        assembly, vt1, _vt2 = self._assembly_three_attendees_two_vote_types()
        a, b = assembly.attendee_ids[0], assembly.attendee_ids[1]
        other_vt = self._create_vote_type(self.env, name="Outside VT", code="OUTVTX")
        with self.assertRaises(ValidationError) as ctx:
            Delegation.create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": a.partner_id.id,
                    "delegate_partner_id": b.partner_id.id,
                    "vote_type_ids": [(6, 0, other_vt.ids)],
                    "delegation_state": "draft",
                }
            )
        self.assertIn("assembly", str(ctx.exception).lower())
