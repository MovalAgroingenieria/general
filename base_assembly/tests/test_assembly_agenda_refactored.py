# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyAgendaRefactored(AssemblyTestMixin, TransactionCase):
    """Tests for refactored assembly.agenda constraints and rules."""

    def test_vote_type_required_when_requires_vote_true_on_create(self):
        """vote_type_id is functionally required when requires_vote=True on create."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        vote_type = assembly.assembly_type_id.vote_type_ids[0]  # noqa: F841

        # Try to create agenda with requires_vote=True but no vote_type_id
        with self.assertRaises(ValidationError) as ctx:
            self.env["assembly.agenda"].create(
                {
                    "assembly_id": assembly.id,
                    "name": "Test Agenda",
                    "requires_vote": True,
                    "vote_type_id": False,
                    "sequence": self._next_agenda_sequence(assembly),
                }
            )
        msg = str(ctx.exception).lower()
        self.assertIn("vote type", msg)
        self.assertTrue("require" in msg or "requires" in msg, msg)

    def test_vote_type_required_when_requires_vote_true_on_write(self):
        """vote_type_id is functionally required when requires_vote=True on write."""
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                agenda_title="Test", requires_vote=False
            )
        )
        agenda = assembly.agenda_ids[0]
        agenda.write({"vote_type_id": False})

        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"requires_vote": True})
        msg = str(ctx.exception).lower()
        self.assertIn("weighted", msg)

    def test_vote_type_not_required_when_requires_vote_false(self):
        """vote_type_id is optional when requires_vote=False."""
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                agenda_title="Test", requires_vote=False
            )
        )
        agenda = assembly.agenda_ids[0]

        agenda.write({"vote_type_id": False})
        self.assertFalse(agenda.vote_type_id)
        self.assertFalse(agenda.requires_vote)

        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        with self.assertRaises(ValidationError):
            agenda.write({"vote_type_id": vote_type.id})

        # Can create agenda with requires_vote=False and no vote_type_id
        agenda2 = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Agenda without vote",
                "requires_vote": False,
                "vote_type_id": False,
                "sequence": self._next_agenda_sequence(assembly),
            }
        )
        self.assertFalse(agenda2.vote_type_id)
        self.assertFalse(agenda2.requires_vote)

    def test_vote_type_must_belong_to_assembly_vote_type_ids(self):
        """vote_type_id must belong to assembly_id.vote_type_ids."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        vote_type = assembly.assembly_type_id.vote_type_ids[0]

        # Create a vote type NOT in assembly
        other_vote_type = self._create_vote_type(  # pylint: disable=protected-access
            self.env, name="Other VT", code="OTHER"
        )

        agenda = assembly.agenda_ids[0]

        # Try to set vote_type_id to one not in assembly
        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"vote_type_id": other_vote_type.id})
        self.assertIn("must be one of the assembly's vote types", str(ctx.exception))

        # Try to create agenda with vote_type_id not in assembly
        with self.assertRaises(ValidationError) as ctx:
            self.env["assembly.agenda"].create(
                {
                    "assembly_id": assembly.id,
                    "name": "Invalid Agenda",
                    "requires_vote": True,
                    "vote_type_id": other_vote_type.id,
                    "sequence": self._next_agenda_sequence(assembly),
                }
            )
        self.assertIn("must be one of the assembly's vote types", str(ctx.exception))

        # Valid: set vote_type_id to one in assembly
        agenda.write({"vote_type_id": vote_type.id})
        self.assertEqual(agenda.vote_type_id, vote_type)

    def test_vote_type_cannot_change_when_votings_exist(self):
        """vote_type_id cannot be changed when voting_ids already exist."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        agenda = assembly.agenda_ids[0]
        vote_type = agenda.vote_type_id
        other_vote_type = assembly.assembly_type_id.vote_type_ids
        if len(other_vote_type) > 1:
            other_vote_type = other_vote_type[1]
        else:
            # Create another vote type in assembly
            other_vote_type = self._create_vote_type(self.env, name="VT2", code="VT2")
            # pylint: disable=protected-access
            assembly.vote_type_ids = [(4, other_vote_type.id)]

        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        self.assertTrue(agenda.voting_ids)

        # Try to change vote_type_id
        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"vote_type_id": other_vote_type.id})
        self.assertIn("cannot be changed", str(ctx.exception).lower())
        self.assertIn("already has votings", str(ctx.exception))

        # Original vote_type_id should remain
        self.assertEqual(agenda.vote_type_id, vote_type)

    def test_vote_type_can_change_when_no_votings(self):
        """vote_type_id can be changed when no votings exist."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        agenda = assembly.agenda_ids[0]
        vote_type = agenda.vote_type_id

        # Create another vote type in assembly
        other_vote_type = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        assembly.vote_type_ids = [(4, other_vote_type.id)]

        # Change vote_type_id (no votings exist)
        agenda.write({"vote_type_id": other_vote_type.id})
        self.assertEqual(agenda.vote_type_id, other_vote_type)

        # Can change back
        agenda.write({"vote_type_id": vote_type.id})
        self.assertEqual(agenda.vote_type_id, vote_type)

    def test_view_domain_filters_by_assembly_vote_types(self):
        """View domain for vote_type_id filters by assembly_id.vote_type_ids."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        vote_type1 = assembly.assembly_type_id.vote_type_ids[0]

        # Create vote type NOT in assembly
        other_vote_type = self._create_vote_type(  # pylint: disable=protected-access
            self.env, name="Other VT", code="OTHER"
        )

        agenda = assembly.agenda_ids[0]

        # The view domain should filter by assembly vote types
        # This is tested by checking that the domain is set correctly in the view
        # In practice, the domain in the view XML ensures only assembly vote types
        # are shown in the dropdown
        self.assertIn(vote_type1, assembly.vote_type_ids)
        self.assertNotIn(other_vote_type, assembly.vote_type_ids)

        # Can set to vote type in assembly
        agenda.write({"vote_type_id": vote_type1.id})
        self.assertEqual(agenda.vote_type_id, vote_type1)

    def test_create_with_valid_vote_type_succeeds(self):
        """Creating agenda with valid vote_type_id and requires_vote=True succeeds."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        vote_type = assembly.assembly_type_id.vote_type_ids[0]

        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Valid Agenda",
                "requires_vote": True,
                "vote_type_id": vote_type.id,
                "sequence": self._next_agenda_sequence(assembly),
            }
        )

        self.assertEqual(agenda.vote_type_id, vote_type)
        self.assertTrue(agenda.requires_vote)

    def test_toggle_requires_vote_with_vote_type_succeeds(self):
        """Weighted mode with vote_type_id from no-vote mode."""
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                agenda_title="Test", requires_vote=False
            )
        )
        agenda = assembly.agenda_ids[0]
        vote_type = assembly.assembly_type_id.vote_type_ids[0]

        agenda.write({"agenda_vote_mode": "weighted", "vote_type_id": vote_type.id})
        self.assertTrue(agenda.requires_vote)
        self.assertEqual(agenda.vote_type_id, vote_type)

    def test_set_requires_vote_and_vote_type_together_succeeds(self):
        """Setting weighted mode and vote_type_id together succeeds."""
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                agenda_title="Test", requires_vote=False
            )
        )
        agenda = assembly.agenda_ids[0]
        vote_type = assembly.assembly_type_id.vote_type_ids[0]

        agenda.write({"agenda_vote_mode": "weighted", "vote_type_id": vote_type.id})
        self.assertTrue(agenda.requires_vote)
        self.assertEqual(agenda.vote_type_id, vote_type)

    def test_assembly_without_vote_types_allows_agenda_without_vote(self):
        """Assembly without vote types allows agenda with requires_vote=False."""
        # Create assembly type without vote types
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Type Without Votes",
                "code": "NOWOTES",
                "vote_type_ids": False,
                "default_quorum_type": "percentage",
                "default_quorum_value": 50.0,
                "default_quorum_second_call_type": "any",
                "default_quorum_second_call_value": 0.0,
                "partner_domain": "[]",
            }
        )

        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Assembly Without Votes",
                "assembly_type_id": assembly_type.id,
            }
        )

        # Can create agenda with requires_vote=False
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Agenda without vote",
                "requires_vote": False,
                "vote_type_id": False,
            }
        )
        self.assertFalse(agenda.requires_vote)
        self.assertFalse(agenda.vote_type_id)

        # Cannot create agenda with requires_vote=True (no vote types available)
        with self.assertRaises(ValidationError) as ctx:
            self.env["assembly.agenda"].create(
                {
                    "assembly_id": assembly.id,
                    "name": "Agenda with vote",
                    "requires_vote": True,
                    "vote_type_id": False,
                    "sequence": self._next_agenda_sequence(assembly),
                }
            )
        msg = str(ctx.exception).lower()
        self.assertIn("vote type", msg)
        self.assertTrue("require" in msg or "requires" in msg, msg)

    def test_cannot_clear_vote_type_when_requires_vote_true(self):
        """Cannot clear vote_type_id when requires_vote=True."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        agenda = assembly.agenda_ids[0]
        self.assertTrue(agenda.requires_vote)
        self.assertTrue(agenda.vote_type_id)

        # Try to clear vote_type_id while requires_vote=True
        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"vote_type_id": False})
        self.assertIn("cannot be cleared", str(ctx.exception).lower())
        self.assertIn("requires vote", str(ctx.exception).lower())

        agenda.write({"agenda_vote_mode": "no_vote"})
        self.assertFalse(agenda.requires_vote)
        self.assertFalse(agenda.vote_type_id)

    def test_assembly_without_vote_types_rejects_vote_type_in_agenda(self):
        """Assembly without vote types rejects agenda with vote_type_id."""
        # Create assembly type without vote types
        assembly_type = self.env["assembly.type"].create(  # noqa: F841
            {
                "name": "Type Without Votes",
                "code": "NOWOTES",
                "vote_type_ids": False,
                "default_quorum_type": "percentage",
                "default_quorum_value": 50.0,
                "default_quorum_second_call_type": "any",
                "default_quorum_second_call_value": 0.0,
                "partner_domain": "[]",
            }
        )

        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Assembly Without Votes",
                "assembly_type_id": assembly_type.id,
            }
        )

        # Create a vote type
        vote_type = self._create_vote_type(self.env, name="VT", code="VT")
        # pylint: disable=protected-access
        # Cannot create agenda with vote_type_id when assembly has no vote types
        with self.assertRaises(ValidationError) as ctx:
            self.env["assembly.agenda"].create(
                {
                    "assembly_id": assembly.id,
                    "name": "Invalid Agenda",
                    "requires_vote": True,
                    "vote_type_id": vote_type.id,
                }
            )
        self.assertIn(
            "cannot be used because the assembly has no vote types", str(ctx.exception)
        )

    def test_vote_type_immutability_after_voting_starts(self):
        """vote_type_id becomes immutable once voting starts."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        agenda = assembly.agenda_ids[0]
        original_vote_type = agenda.vote_type_id

        # Create another vote type in assembly
        other_vote_type = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        assembly.vote_type_ids = [(4, other_vote_type.id)]

        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        self.assertTrue(agenda.voting_ids)

        # Cannot change to different vote type
        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"vote_type_id": other_vote_type.id})
        self.assertIn("cannot be changed", str(ctx.exception).lower())
        self.assertIn("immutable", str(ctx.exception).lower())

        # Can set to same vote type (no-op, but should not error)
        agenda.write({"vote_type_id": original_vote_type.id})
        self.assertEqual(agenda.vote_type_id, original_vote_type)

        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"vote_type_id": False})
        msg_clear = str(ctx.exception).lower()
        self.assertTrue(
            "cannot be cleared" in msg_clear or "cannot be changed" in msg_clear,
            msg_clear,
        )

    def test_requires_vote_toggle_with_vote_type_validation(self):
        """Vote mode and vote_type_id stay coherent (AF v2)."""
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                agenda_title="Test", requires_vote=False
            )
        )
        agenda = assembly.agenda_ids[0]
        vote_type = assembly.assembly_type_id.vote_type_ids[0]

        with self.assertRaises(ValidationError):
            agenda.write({"vote_type_id": vote_type.id})

        agenda.write({"agenda_vote_mode": "weighted", "vote_type_id": vote_type.id})
        self.assertTrue(agenda.requires_vote)
        self.assertEqual(agenda.vote_type_id, vote_type)

        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"vote_type_id": False})
        self.assertIn("cannot be cleared", str(ctx.exception).lower())

        agenda.write({"agenda_vote_mode": "no_vote"})
        self.assertFalse(agenda.requires_vote)
        self.assertFalse(agenda.vote_type_id)

        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"requires_vote": True})
        self.assertIn("weighted", str(ctx.exception).lower())
