# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyAttendeeVote(AssemblyTestMixin, TransactionCase):
    """Tests for assembly.attendee.vote: compute total, uniqueness."""

    def test_attendee_vote_total_is_own_minus_out_plus_in(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        self._give_partner_votes(
            att.partner_id, vote_type, 10
        )  # pylint: disable=protected-access
        att.action_confirm()
        av = self.env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", att.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertEqual(av.own_votes, 10.0)
        self.assertEqual(av.delegated_out_votes, 0.0)
        self.assertEqual(av.delegated_in_votes, 0.0)
        self.assertEqual(av.attendee_vote_total, 10.0)

    def test_attendee_vote_total_with_delegation_out(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 5)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type, 2)
        # pylint: disable=protected-access
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
        av_delegator = self.env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", delegator.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        av_delegate = self.env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", delegate.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertEqual(av_delegator.own_votes, 5.0)
        self.assertEqual(av_delegator.delegated_out_votes, 5.0)
        self.assertEqual(av_delegator.delegated_in_votes, 0.0)
        self.assertEqual(av_delegator.attendee_vote_total, 0.0)
        self.assertEqual(av_delegate.delegated_in_votes, 5.0)
        self.assertEqual(av_delegate.attendee_vote_total, 2.0 + 5.0)

    def test_unique_attendee_vote_type_prevents_duplicate(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        Av = self.env["assembly.attendee.vote"]
        if not Av.search(
            [
                ("attendee_id", "=", att.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        ):
            Av.create(
                {
                    "attendee_id": att.id,
                    "vote_type_id": vote_type.id,
                    "own_votes": 1.0,
                }
            )
        with self.assertRaises(Exception):
            Av.create(
                {
                    "attendee_id": att.id,
                    "vote_type_id": vote_type.id,
                    "own_votes": 2.0,
                }
            )
