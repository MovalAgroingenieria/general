# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyVoting(AssemblyTestMixin, TransactionCase):
    """Tests for assembly.voting and assembly.voting.line: create, close,
    results, constraints."""

    def test_add_voting_line_updates_total_votes_cast(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att1 = assembly.attendee_ids[0]
        att2 = assembly.attendee_ids[1]
        self._give_partner_votes(
            att1.partner_id, vote_type, 3
        )  # pylint: disable=protected-access
        self._give_partner_votes(
            att2.partner_id, vote_type, 2
        )  # pylint: disable=protected-access
        att1.action_confirm()
        att2.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.assertEqual(voting.total_votes_cast, 0.0)
        self.assertEqual(voting.total_votes_possible, 5.0)
        self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att1.id,
                "vote_option": "yes",
                "votes_applied": 3.0,
            }
        )
        voting.invalidate_recordset()
        self.assertEqual(voting.total_votes_cast, 3.0)
        self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att2.id,
                "vote_option": "no",
                "votes_applied": 2.0,
            }
        )
        voting.invalidate_recordset()
        self.assertEqual(voting.total_votes_cast, 5.0)

    def test_votes_applied_must_equal_attendee_vote_total(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(
            att.partner_id, vote_type, 4
        )  # pylint: disable=protected-access
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

    def test_attendee_with_zero_votes_cannot_have_line(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(
            att.partner_id, vote_type, 0
        )  # pylint: disable=protected-access
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
                    "votes_applied": 0.0,
                }
            )
        self.assertIn("no votes", str(ctx.exception).lower())

    def test_unique_voting_attendee_prevents_duplicate_line(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(
            att.partner_id, vote_type, 1
        )  # pylint: disable=protected-access
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
            self.env["assembly.voting.line"].create(
                {
                    "voting_id": voting.id,
                    "attendee_id": att.id,
                    "vote_option": "no",
                    "votes_applied": 1.0,
                }
            )

    def test_create_line_when_voting_closed_raises(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(
            att.partner_id, vote_type, 1
        )  # pylint: disable=protected-access
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

    def test_action_close_creates_results_and_sets_agenda_voted(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(
            att.partner_id, vote_type, 2
        )  # pylint: disable=protected-access
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
        self.assertTrue(voting.date_close)
        self.assertEqual(agenda.agenda_state, "voted")
        self.assertEqual(len(voting.result_ids), 5)
        options = set(voting.result_ids.mapped("vote_option"))  # noqa: F841
        self.assertEqual(
            options,
            {"yes", "no", "abstention", "blank", "not_cast"},
        )
        yes_result = voting.result_ids.filtered(
            lambda r: r.vote_option == "yes"
        )  # noqa: F841
        self.assertEqual(yes_result.total_votes, 2.0)
        not_cast_result = voting.result_ids.filtered(  # noqa: F841
            lambda r: r.vote_option == "not_cast"
        )
        self.assertEqual(not_cast_result.total_votes, 0.0)

    def test_close_already_closed_voting_raises(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
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

    def test_new_voting_line_has_channel_and_cast_at_defaults(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]  # noqa: F841
        att = assembly.attendee_ids[0]
        self._give_partner_votes(
            att.partner_id, vote_type, 1
        )  # pylint: disable=protected-access
        att.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        line = self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att.id,
                "vote_option": "yes",
                "votes_applied": 1.0,
            }
        )
        self.assertEqual(line.vote_channel, "in_person")
        self.assertTrue(line.vote_cast_at)
