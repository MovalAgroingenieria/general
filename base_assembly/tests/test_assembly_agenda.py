# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyAgenda(AssemblyTestMixin, TransactionCase):
    """Tests for assembly.agenda: start_voting, skip, constraints."""

    def test_action_start_voting_creates_voting_open_and_sets_agenda_in_progress(self):
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        self.assertEqual(agenda.agenda_state, "pending")
        agenda.action_start_voting()
        self.assertEqual(agenda.agenda_state, "in_progress")
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.assertTrue(voting)
        self.assertEqual(voting.voting_state, "open")
        self.assertTrue(voting.date_open)

    def test_action_start_voting_without_vote_type_raises(self):
        assembly, agenda = self._create_assembly_with_agenda(
            agenda_title="Sin tipo", requires_vote=True
        )
        agenda.vote_type_id = False
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        with self.assertRaises(ValidationError) as ctx:
            agenda.action_start_voting()
        self.assertIn("vote type", str(ctx.exception).lower())

    def test_action_start_voting_when_not_pending_or_in_progress_raises(self):
        assembly, agenda = self._create_assembly_with_agenda()
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

    def test_action_skip_sets_agenda_state_skipped(self):
        assembly, agenda = self._create_assembly_with_agenda()
        self.assertEqual(agenda.agenda_state, "pending")
        agenda.action_skip()
        self.assertEqual(agenda.agenda_state, "skipped")

    def test_vote_type_must_be_in_assembly_types(self):
        assembly, agenda = self._create_assembly_with_agenda()
        other_vote_type = self._create_vote_type(
            self.env, name="Other type", code="OTHER"
        )
        with self.assertRaises(ValidationError) as ctx:
            agenda.vote_type_id = other_vote_type.id
        self.assertIn("assembly's vote types", str(ctx.exception))

    def test_cannot_change_vote_type_when_votings_exist(self):
        vote_type1 = self._create_vote_type(self.env, name="VT1", code="VT1")
        vote_type2 = self._create_vote_type(self.env, name="VT2", code="VT2")
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Type two",
                "code": "TWO",
                "vote_type_ids": [(6, 0, (vote_type1 | vote_type2).ids)],
                "partner_domain": "[]",
            }
        )
        partners = self._create_partners(self.env, 2)
        assembly, agenda = self._create_assembly_with_agenda(
            assembly_type=assembly_type,
            partner_domain="[('id', 'in', %s)]" % partners.ids,
        )
        agenda.vote_type_id = vote_type1
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"vote_type_id": vote_type2.id})
        self.assertIn("already has votings", str(ctx.exception))
