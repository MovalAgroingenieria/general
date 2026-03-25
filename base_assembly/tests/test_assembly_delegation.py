# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyDelegation(AssemblyTestMixin, TransactionCase):
    """Tests for assembly.delegation: constraints, confirm, recompute."""

    def test_create_delegation_different_partners_succeeds(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        delegator = assembly.attendee_ids[0].partner_id
        delegate = assembly.attendee_ids[1].partner_id
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.id,
                "delegate_partner_id": delegate.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        self.assertEqual(delegation.delegation_state, "draft")

    def test_delegator_equals_delegate_raises(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        partner = assembly.attendee_ids[0].partner_id
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

    def test_delegate_outside_partner_domain_raises(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        delegator = assembly.attendee_ids[0].partner_id
        outside_partner = self.env["res.partner"].create(
            {"name": "Outside", "is_company": False}
        )
        self.env["assembly.attendee"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": outside_partner.id,
            }
        )
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        with self.assertRaises(ValidationError) as ctx:
            self.env["assembly.delegation"].create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": delegator.id,
                    "delegate_partner_id": outside_partner.id,
                    "vote_type_ids": [(6, 0, vote_type.ids)],
                }
            )
        self.assertIn("convocable", str(ctx.exception).lower())

    def test_confirm_delegation_updates_attendee_votes(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 4)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        # pylint: disable=protected-access
        delegator.action_confirm()
        delegate.action_confirm()
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "draft",
            }
        )
        delegation.delegation_state = "confirmed"
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()
        av_delegate = self.env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", delegate.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertEqual(av_delegate.delegated_in_votes, 4.0)
        self.assertEqual(av_delegate.attendee_vote_total, 1.0 + 4.0)

    def test_two_confirmed_delegations_same_type_raises(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0].partner_id
        delegate1 = assembly.attendee_ids[1].partner_id
        delegate2 = assembly.attendee_ids[2].partner_id
        assembly.attendee_ids[1].action_confirm()
        assembly.attendee_ids[2].action_confirm()
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
        self.assertIn("same vote type", str(ctx.exception).lower())
