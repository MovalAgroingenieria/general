# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Votes: totals, non-attendee delegator inbound, eligibility, recompute, frozen cast.

Chaining is asserted in ``test_delegation_no_chain`` and quorum/delegation suites.
Cancelled-assembly quorum: ``test_quorum_people_functional_spec``.
"""

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestVotes(AssemblyTestMixin, TransactionCase):
    """``assembly.attendee.vote`` persistence and ``assembly.voting.line`` constraints."""

    @staticmethod
    def _attendee_vote_line(env, attendee, vote_type):
        return env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", attendee.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
            order="id",
        )

    def test_non_attendee_delegator_transfers_votes(self):
        """Rule 6: delegator without attendee row; ``delegated_in`` from ``partner.vote``."""
        env = self.env
        p_a = env["res.partner"].create(
            {"name": "Votes ExtA", "is_company": False, "assembly_excluded": True}
        )
        p_b = env["res.partner"].create(
            {"name": "Votes DelB", "is_company": False, "assembly_excluded": False}
        )
        domain = "[('id', 'in', %s)]" % ([p_a.id, p_b.id],)
        assembly, _agenda = self._create_assembly_with_agenda(partner_domain=domain)
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        self._give_partner_votes(p_a, vote_type, 8)
        self._give_partner_votes(p_b, vote_type, 2)
        b_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_b)
        b_att.action_confirm()
        env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_a.id,
                "delegate_partner_id": p_b.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        line_b = self._attendee_vote_line(env, b_att, vote_type)
        self.assertTrue(line_b)
        self.assertEqual(line_b.delegated_in_votes, 8.0)
        self.assertEqual(line_b.own_votes, 2.0)
        self.assertEqual(line_b.attendee_vote_total, 10.0)

    def test_attendee_vote_total_formula(self):
        """Rule 4: stored total matches own - delegated_out + delegated_in."""
        env = self.env
        assembly, _agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        a_att, b_att = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(a_att.partner_id, vote_type, 5)
        self._give_partner_votes(b_att.partner_id, vote_type, 2)
        (a_att | b_att).action_confirm()
        env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": a_att.partner_id.id,
                "delegate_partner_id": b_att.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        line_a = self._attendee_vote_line(env, a_att, vote_type)
        line_b = self._attendee_vote_line(env, b_att, vote_type)
        self.assertEqual(
            line_a.attendee_vote_total,
            line_a.own_votes - line_a.delegated_out_votes + line_a.delegated_in_votes,
        )
        self.assertEqual(
            line_b.attendee_vote_total,
            line_b.own_votes - line_b.delegated_out_votes + line_b.delegated_in_votes,
        )
        self.assertEqual(line_a.delegated_out_votes, 5.0)
        self.assertEqual(line_a.attendee_vote_total, 0.0)
        self.assertEqual(line_b.delegated_in_votes, 5.0)
        self.assertEqual(line_b.attendee_vote_total, 7.0)

    def test_attendee_with_zero_votes_cannot_vote(self):
        """Rule 5: ``attendee_vote_total <= 0`` blocks ``assembly.voting.line`` create."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator, delegate = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 3)
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        (delegator | delegate).action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        line_del = self._attendee_vote_line(self.env, delegator, vote_type)
        self.assertLessEqual(line_del.attendee_vote_total, 0.0)
        voting = self._open_voting_on_agenda(assembly, agenda)
        with self.assertRaises(ValidationError) as ex:
            self.env["assembly.voting.line"].create(
                {
                    "voting_id": voting.id,
                    "attendee_id": delegator.id,
                    "vote_option": "yes",
                    "votes_applied": 0.0,
                }
            )
        self.assertIn("no votes", str(ex.exception).lower())

    def test_vote_recompute_is_deterministic(self):
        """Rule 9: repeated recompute leaves the same persisted components."""
        assembly, _agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        a_att, b_att = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(a_att.partner_id, vote_type, 4)
        self._give_partner_votes(b_att.partner_id, vote_type, 1)
        (a_att | b_att).action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": a_att.partner_id.id,
                "delegate_partner_id": b_att.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        line_b = self._attendee_vote_line(self.env, b_att, vote_type)
        first = (
            line_b.own_votes,
            line_b.delegated_out_votes,
            line_b.delegated_in_votes,
            line_b.attendee_vote_total,
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        line_b.invalidate_recordset()
        line_b = self._attendee_vote_line(self.env, b_att, vote_type)
        second = (
            line_b.own_votes,
            line_b.delegated_out_votes,
            line_b.delegated_in_votes,
            line_b.attendee_vote_total,
        )
        self.assertEqual(first, second)

    def test_no_duplicate_attendee_votes(self):
        """Rule 8: one persisted row per (attendee, vote_type) after many recomputes."""
        assembly, _agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        a_att, b_att = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(a_att.partner_id, vote_type, 6)
        self._give_partner_votes(b_att.partner_id, vote_type, 2)
        (a_att | b_att).action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": a_att.partner_id.id,
                "delegate_partner_id": b_att.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        Av = self.env["assembly.attendee.vote"]
        for _ in range(12):
            assembly.attendee_ids.recompute_attendee_vote_lines()
        self.assertEqual(
            Av.search_count(
                [
                    ("attendee_id", "in", (a_att | b_att).ids),
                    ("vote_type_id", "=", vote_type.id),
                ]
            ),
            2,
        )

    def test_votes_applied_is_frozen(self):
        """Rule 10: cast line keeps ``votes_applied`` when underlying totals change later."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vote_type, 3)
        att.action_confirm()
        att.recompute_attendee_vote_lines()
        voting = self._open_voting_on_agenda(assembly, agenda)
        line = self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att.id,
                "vote_option": "yes",
                "votes_applied": 3.0,
            }
        )
        self._give_partner_votes(att.partner_id, vote_type, 50)
        assembly.attendee_ids.recompute_attendee_vote_lines()
        line.invalidate_recordset()
        self.assertEqual(line.votes_applied, 3.0)
        av = self._attendee_vote_line(self.env, att, vote_type)
        self.assertGreater(av.attendee_vote_total, 3.0)

    def test_create_without_votes_applied_stores_attendee_total_snapshot(self):
        """At emit time, server copies attendee vote total into ``votes_applied``."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vote_type, 5)
        att.action_confirm()
        att.recompute_attendee_vote_lines()
        av_before = self._attendee_vote_line(self.env, att, vote_type)
        self.assertEqual(av_before.attendee_vote_total, 5.0)
        voting = self._open_voting_on_agenda(assembly, agenda)
        line = self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att.id,
                "vote_option": "yes",
            }
        )
        self.assertEqual(line.votes_applied, 5.0)

    def test_recompute_after_cast_leaves_votes_applied_unchanged(self):
        """Persisted ``votes_applied`` does not follow later attendee line recomputes."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vote_type, 2)
        att.action_confirm()
        att.recompute_attendee_vote_lines()
        voting = self._open_voting_on_agenda(assembly, agenda)
        line = self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att.id,
                "vote_option": "yes",
                "votes_applied": 2.0,
            }
        )
        self._give_partner_votes(att.partner_id, vote_type, 99)
        assembly.attendee_ids.recompute_attendee_vote_lines()
        line.invalidate_recordset()
        self.assertEqual(line.votes_applied, 2.0)

    def test_write_vote_option_after_total_change_preserves_votes_applied(self):
        """Updating another field after totals move does not alter the snapshot."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vote_type, 4)
        att.action_confirm()
        att.recompute_attendee_vote_lines()
        voting = self._open_voting_on_agenda(assembly, agenda)
        line = self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att.id,
                "vote_option": "yes",
                "votes_applied": 4.0,
            }
        )
        self._give_partner_votes(att.partner_id, vote_type, 10)
        assembly.attendee_ids.recompute_attendee_vote_lines()
        line.write({"vote_option": "no"})
        line.invalidate_recordset()
        self.assertEqual(line.votes_applied, 4.0)

    def test_cannot_write_votes_applied_after_cast(self):
        """``votes_applied`` is immutable after the line exists."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vote_type, 1)
        att.action_confirm()
        att.recompute_attendee_vote_lines()
        voting = self._open_voting_on_agenda(assembly, agenda)
        line = self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att.id,
                "vote_option": "yes",
                "votes_applied": 1.0,
            }
        )
        with self.assertRaises(ValidationError) as ex:
            line.write({"votes_applied": 9.0})
        self.assertIn("frozen", str(ex.exception).lower())

    def test_votes_applied_unchanged_when_second_delegation_increases_delegate_total(
        self,
    ):
        """After casting the vote, a new delegation may raise delegate total; ``votes_applied`` does not."""
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        a_att, b_att, c_att = assembly.attendee_ids.sorted("id")
        self._give_partner_votes(a_att.partner_id, vote_type, 5)
        self._give_partner_votes(b_att.partner_id, vote_type, 1)
        self._give_partner_votes(c_att.partner_id, vote_type, 3)
        (a_att | b_att | c_att).action_confirm()
        Delegation = self.env["assembly.delegation"]
        Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": a_att.partner_id.id,
                "delegate_partner_id": b_att.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        b_line = self.env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", b_att.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertEqual(b_line.attendee_vote_total, 6.0)
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        cast = self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": b_att.id,
                "vote_option": "yes",
                "votes_applied": 6.0,
                "vote_channel": "in_person",
            }
        )
        Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": c_att.partner_id.id,
                "delegate_partner_id": b_att.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        b_line.invalidate_recordset()
        b_line = self.env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", b_att.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertEqual(b_line.attendee_vote_total, 9.0)
        cast.invalidate_recordset()
        self.assertEqual(cast.votes_applied, 6.0)
