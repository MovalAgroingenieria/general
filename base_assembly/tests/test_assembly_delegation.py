# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyDelegation(AssemblyTestMixin, TransactionCase):
    """Tests for assembly.delegation: constraints, vote snapshots, unlink."""

    def test_create_delegation_before_delegate_confirm_has_no_vote_transfer(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        self._give_partner_votes(delegator.partner_id, vote_type, 1)
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        delegator.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        delegator.recompute_attendee_vote_lines()
        line = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(line.delegated_out_votes, 0.0)
        delegate.action_confirm()
        delegator.recompute_attendee_vote_lines()
        line = delegator.attendee_vote_ids.filtered(
            lambda v: v.vote_type_id == vote_type
        )
        self.assertEqual(line.delegated_out_votes, 1.0)

    def test_create_delegation_different_partners_succeeds(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        self._give_partner_votes(delegator.partner_id, vote_type, 1)
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        delegator.action_confirm()
        delegate.action_confirm()
        delegation = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        self.assertTrue(delegation.id)

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

    def test_create_delegation_updates_attendee_votes(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
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
            }
        )
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

    def test_unlink_delegation_recomputes_attendee_vote_lines(self):
        """Removing a delegation must clear stale delegated_in/out on stored snapshots."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 6)
        self._give_partner_votes(delegate.partner_id, vote_type, 2)
        delegator.action_confirm()
        delegate.action_confirm()
        delegation = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        av_del = self.env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", delegate.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertEqual(av_del.delegated_in_votes, 6.0)
        delegation.unlink()
        av_del = self.env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", delegate.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertEqual(av_del.delegated_in_votes, 0.0)
        self.assertEqual(av_del.attendee_vote_total, 2.0)
        av_out = self.env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", delegator.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertEqual(av_out.delegated_out_votes, 0.0)

    def test_two_delegations_same_type_raises(self):
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
            }
        )
        with self.assertRaises(ValidationError) as ctx:
            self.env["assembly.delegation"].create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": delegator.id,
                    "delegate_partner_id": delegate2.id,
                    "vote_type_ids": [(6, 0, vote_type.ids)],
                }
            )
        self.assertIn("same vote type", str(ctx.exception).lower())

    def test_write_changes_delegator_partner_recomputes_delegate_delegated_in(self):
        """Changing ``partner_id`` on a delegation must refresh stored snapshots."""
        env = self.env
        p_del_a = env["res.partner"].create(
            {"name": "DelA", "is_company": False, "assembly_excluded": True}
        )
        p_del_b = env["res.partner"].create(
            {"name": "DelB", "is_company": False, "assembly_excluded": True}
        )
        p_def = env["res.partner"].create(
            {"name": "Delegate", "is_company": False, "assembly_excluded": False}
        )
        domain = "[('id', 'in', %s)]" % ([p_del_a.id, p_del_b.id, p_def.id],)
        assembly, _ = self._create_assembly_with_agenda(partner_domain=domain)
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        self._give_partner_votes(p_del_a, vote_type, 10)
        self._give_partner_votes(p_del_b, vote_type, 3)
        self._give_partner_votes(p_def, vote_type, 2)
        delegate_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_def)
        delegate_att.action_confirm()
        del_a_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_del_a)
        del_b_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_del_b)
        del_a_att.action_confirm()
        del_b_att.action_confirm()
        del_rec = env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_del_a.id,
                "delegate_partner_id": p_def.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        av = env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", delegate_att.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertEqual(av.delegated_in_votes, 10.0)
        del_rec.write({"partner_id": p_del_b.id})
        av = env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", delegate_att.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertEqual(av.delegated_in_votes, 3.0)
