# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyAgenda(AssemblyTestMixin, TransactionCase):
    """Tests for assembly.agenda: start_voting, skip, constraints."""

    def test_action_start_voting_creates_voting_open_and_sets_agenda_in_progress(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        self.assertEqual(agenda.agenda_state, "pending")
        action = agenda.action_start_voting()
        self.assertEqual(agenda.agenda_state, "in_progress")
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.assertTrue(voting)
        self.assertEqual(voting.voting_state, "open")
        self.assertTrue(voting.date_open)
        self.assertEqual(action.get("type"), "ir.actions.act_window")
        self.assertEqual(action.get("res_model"), "assembly.voting")
        self.assertEqual(action.get("res_id"), voting.id)
        self.assertEqual(action.get("view_mode"), "form")

    def test_action_start_voting_without_vote_type_raises(self):
        assembly, agenda = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                agenda_title="No vote type", requires_vote=True
            )
        )
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        # ORM forbids clearing vote_type while requires_vote; use SQL for this edge case
        self.env.cr.execute(
            "UPDATE assembly_agenda SET vote_type_id = NULL WHERE id = %s",
            (agenda.id,),
        )
        agenda.invalidate_recordset(["vote_type_id"])
        with self.assertRaises(ValidationError) as ctx:
            agenda.action_start_voting()
        self.assertIn("vote type", str(ctx.exception).lower())

    def test_action_start_voting_when_not_pending_or_in_progress_raises(self):
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
        self.assertEqual(agenda.agenda_state, "voted")
        with self.assertRaises(ValidationError) as ctx:
            agenda.action_start_voting()
        self.assertIn("not open for voting", str(ctx.exception).lower())

    def test_action_start_voting_while_already_open_raises(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        with self.assertRaises(ValidationError) as ctx:
            agenda.action_start_voting()
        self.assertIn("open voting", str(ctx.exception).lower())

    def test_action_skip_sets_agenda_state_skipped(self):
        _, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        self.assertEqual(agenda.agenda_state, "pending")
        agenda.action_skip()
        self.assertEqual(agenda.agenda_state, "skipped")

    def test_vote_type_must_be_in_assembly_types(self):
        _, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        other_vote_type = (
            self._create_vote_type(  # noqa: F841  # pylint: disable=protected-access
                self.env, name="Other type", code="OTHER"
            )
        )
        with self.assertRaises(ValidationError) as ctx:
            agenda.vote_type_id = other_vote_type.id
        self.assertIn("assembly's vote types", str(ctx.exception))

    def test_cannot_change_vote_type_when_votings_exist(self):
        vote_type1 = self._create_vote_type(self.env, name="VT1", code="VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Type two",
                "code": "TWO",
                "vote_type_ids": [(6, 0, (vote_type1 | vote_type2).ids)],
                "partner_domain": "[]",
            }
        )
        partners = self._create_partners(  # noqa: F841
            self.env, 2
        )  # pylint: disable=protected-access
        assembly, agenda = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                assembly_type=assembly_type,
                partner_domain="[('id', 'in', %s)]" % partners.ids,
            )
        )
        agenda.vote_type_id = vote_type1
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"vote_type_id": vote_type2.id})
        self.assertIn("already has votings", str(ctx.exception))
