# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""No chained vote delegations: ORM blocks overlapping A→B→C; out uses base own only."""

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestDelegationNoChain(AssemblyTestMixin, TransactionCase):
    """Chained delegations must be rejected; delegated_out must not use delegated_in."""

    @staticmethod
    def _vote_line(attendee, vote_type):
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

    def _setup_three_confirmed_attendees_two_vote_types(self):
        """Assembly with VT1/VT2 and three partners, all confirmed with votes on both types."""
        env = self.env
        vt1 = self._create_vote_type(env, name="NoChain VT1")
        vt2 = self._create_vote_type(env, name="NoChain VT2")
        atype = self._create_assembly_type(env, name="NoChain type", vote_type=vt1)
        atype.write({"vote_type_ids": [(4, vt2.id)]})
        partners = self._create_partners(env, 3, prefix="NoChain")
        partner_domain = "[('id', 'in', %s)]" % partners.ids
        assembly, _ = self._create_assembly_with_agenda(
            name="No chain assembly",
            assembly_type=atype,
            partner_domain=partner_domain,
        )
        assembly.vote_type_ids = [(6, 0, [vt1.id, vt2.id])]
        assembly.action_generate_attendees()
        attendees = assembly.attendee_ids.sorted("id")
        self.assertEqual(len(attendees), 3)
        for att in attendees:
            self._give_partner_votes(att.partner_id, vt1, 5)
            self._give_partner_votes(att.partner_id, vt2, 5)
        attendees.action_confirm()
        return assembly, vt1, vt2, attendees[0], attendees[1], attendees[2]

    def test_positive_non_overlapping_second_delegation_allowed(self):
        """A→B on VT1 and B→C on VT2: no type overlap, both confirmed delegations allowed."""
        assembly, vt1, vt2, a_att, b_att, c_att = (
            self._setup_three_confirmed_attendees_two_vote_types()
        )
        Delegation = self.env["assembly.delegation"]
        d1 = Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": a_att.partner_id.id,
                "delegate_partner_id": b_att.partner_id.id,
                "vote_type_ids": [(6, 0, [vt1.id])],
                "delegation_state": "confirmed",
            }
        )
        d2 = Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": b_att.partner_id.id,
                "delegate_partner_id": c_att.partner_id.id,
                "vote_type_ids": [(6, 0, [vt2.id])],
                "delegation_state": "confirmed",
            }
        )
        self.assertTrue(d1 and d2)

    def test_negative_cannot_delegate_same_type_while_receiving(self):
        """B already receives VT1 from A → B→C on VT1 must raise ValidationError."""
        assembly, vt1, _vt2, a_att, b_att, c_att = (
            self._setup_three_confirmed_attendees_two_vote_types()
        )
        Delegation = self.env["assembly.delegation"]
        Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": a_att.partner_id.id,
                "delegate_partner_id": b_att.partner_id.id,
                "vote_type_ids": [(6, 0, [vt1.id])],
                "delegation_state": "confirmed",
            }
        )
        with self.assertRaises(ValidationError):
            Delegation.create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": b_att.partner_id.id,
                    "delegate_partner_id": c_att.partner_id.id,
                    "vote_type_ids": [(6, 0, [vt1.id])],
                    "delegation_state": "confirmed",
                }
            )

    def test_negative_cannot_receive_while_delegate_already_delegates_same_type(self):
        """B already delegates VT1 to C → A→B on VT1 must raise ValidationError."""
        assembly, vt1, _vt2, a_att, b_att, c_att = (
            self._setup_three_confirmed_attendees_two_vote_types()
        )
        Delegation = self.env["assembly.delegation"]
        Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": b_att.partner_id.id,
                "delegate_partner_id": c_att.partner_id.id,
                "vote_type_ids": [(6, 0, [vt1.id])],
                "delegation_state": "confirmed",
            }
        )
        with self.assertRaises(ValidationError):
            Delegation.create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": a_att.partner_id.id,
                    "delegate_partner_id": b_att.partner_id.id,
                    "vote_type_ids": [(6, 0, [vt1.id])],
                    "delegation_state": "confirmed",
                }
            )

    def test_regression_single_delegation_still_recomputes_vote_lines(self):
        """One confirmed delegation still moves only delegator base votes (backward compatible)."""
        assembly, vt1, _vt2, a_att, b_att, _c = (
            self._setup_three_confirmed_attendees_two_vote_types()
        )
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": a_att.partner_id.id,
                "delegate_partner_id": b_att.partner_id.id,
                "vote_type_ids": [(6, 0, [vt1.id])],
                "delegation_state": "confirmed",
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        av_a = self._vote_line(a_att, vt1)
        av_b = self._vote_line(b_att, vt1)
        self.assertEqual(av_a.delegated_out_votes, 5.0)
        self.assertEqual(av_a.own_votes, 5.0)
        self.assertEqual(av_b.delegated_in_votes, 5.0)

    def test_regression_delegated_out_zero_when_base_own_zero_despite_inbound(self):
        """Delegate with 0 partner.vote on a type still gets delegated_in but never delegated_out on it."""
        assembly, vt1, _vt2, a_att, b_att, _c = (
            self._setup_three_confirmed_attendees_two_vote_types()
        )
        self.env["partner.vote"].search(
            [
                ("partner_id", "=", b_att.partner_id.id),
                ("vote_type_id", "=", vt1.id),
            ]
        ).unlink()
        self._give_partner_votes(a_att.partner_id, vt1, 10)
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": a_att.partner_id.id,
                "delegate_partner_id": b_att.partner_id.id,
                "vote_type_ids": [(6, 0, [vt1.id])],
                "delegation_state": "confirmed",
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        av_b = self._vote_line(b_att, vt1)
        self.assertEqual(av_b.own_votes, 0.0)
        self.assertEqual(av_b.delegated_in_votes, 10.0)
        self.assertEqual(av_b.delegated_out_votes, 0.0)
