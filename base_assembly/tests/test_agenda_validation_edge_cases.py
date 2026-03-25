# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Production-grade tests for agenda validation edge cases.

Tests edge cases for agenda validation:
- Multiple vote types scenarios
- Vote type changes in assembly
- Complex validation scenarios
- Boundary conditions
"""

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAgendaValidationEdgeCases(AssemblyTestMixin, TransactionCase):
    """Test agenda validation edge cases comprehensively."""

    def test_agenda_with_multiple_vote_types_validation(self):
        """Agenda validation works correctly with multiple vote types."""
        # Create assembly with multiple vote types
        vote_type1 = self._create_vote_type(self.env, name="VT1", code="VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        vote_type3 = self._create_vote_type(self.env, name="VT3", code="VT3")
        # pylint: disable=protected-access
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Multi Type",
                "code": "MULTI",
                "vote_type_ids": [
                    (6, 0, [vote_type1.id, vote_type2.id, vote_type3.id])
                ],
                "default_quorum_type": "percentage",
                "default_quorum_value": 50.0,
                "default_quorum_second_call_type": "any",
                "default_quorum_second_call_value": 0.0,
                "partner_domain": "[]",
            }
        )
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Multi Type Assembly",
                "assembly_type_id": assembly_type.id,
            }
        )

        # Create agenda with vote_type1
        agenda1 = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Agenda 1",
                "requires_vote": True,
                "vote_type_id": vote_type1.id,
                "sequence": 10,
            }
        )
        self.assertEqual(agenda1.vote_type_id, vote_type1)

        # Create agenda with vote_type2
        agenda2 = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Agenda 2",
                "requires_vote": True,
                "vote_type_id": vote_type2.id,
                "sequence": 20,
            }
        )
        self.assertEqual(agenda2.vote_type_id, vote_type2)

        # Try to set vote_type3 to agenda1 (should succeed, no votings)
        agenda1.write({"vote_type_id": vote_type3.id})
        self.assertEqual(agenda1.vote_type_id, vote_type3)

    def test_agenda_vote_type_change_when_assembly_vote_types_change(self):
        """Agenda vote_type_id validation when assembly vote_types change."""
        vote_type1 = self._create_vote_type(self.env, name="VT1", code="VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        vote_type3 = self._create_vote_type(self.env, name="VT3", code="VT3")
        # pylint: disable=protected-access
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Test Type",
                "code": "TEST",
                "vote_type_ids": [(6, 0, [vote_type1.id, vote_type2.id])],
                "default_quorum_type": "percentage",
                "default_quorum_value": 50.0,
                "default_quorum_second_call_type": "any",
                "default_quorum_second_call_value": 0.0,
                "partner_domain": "[]",
            }
        )
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Test Assembly",
                "assembly_type_id": assembly_type.id,
            }
        )

        # Create agenda with vote_type1
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Test Agenda",
                "requires_vote": True,
                "vote_type_id": vote_type1.id,
            }
        )
        self.assertEqual(agenda.vote_type_id, vote_type1)

        # Remove vote_type1 from assembly, add vote_type3
        assembly.vote_type_ids = [(6, 0, [vote_type2.id, vote_type3.id])]

        # Agenda still has vote_type1 (not in assembly anymore)
        # Should fail validation on next write
        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"name": "Updated"})  # Trigger constraint
        self.assertIn("must be one of the assembly's vote types", str(ctx.exception))

        # Can change to vote_type2 (in assembly)
        agenda.write({"vote_type_id": vote_type2.id})
        self.assertEqual(agenda.vote_type_id, vote_type2)

    def test_agenda_requires_vote_toggle_with_multiple_types(self):
        """Toggle requires_vote with multiple vote types available."""
        vote_type1 = self._create_vote_type(self.env, name="VT1", code="VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Multi Type",
                "code": "MULTI",
                "vote_type_ids": [(6, 0, [vote_type1.id, vote_type2.id])],
                "default_quorum_type": "percentage",
                "default_quorum_value": 50.0,
                "default_quorum_second_call_type": "any",
                "default_quorum_second_call_value": 0.0,
                "partner_domain": "[]",
            }
        )
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Multi Type Assembly",
                "assembly_type_id": assembly_type.id,
            }
        )

        # Create agenda without vote
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Test Agenda",
                "requires_vote": False,
                "vote_type_id": False,
            }
        )

        # Set vote_type1
        agenda.write({"vote_type_id": vote_type1.id})

        # Enable requires_vote (should succeed)
        agenda.write({"requires_vote": True})
        self.assertTrue(agenda.requires_vote)
        self.assertEqual(agenda.vote_type_id, vote_type1)

        # Change to vote_type2 (should succeed, no votings)
        agenda.write({"vote_type_id": vote_type2.id})
        self.assertEqual(agenda.vote_type_id, vote_type2)

        # Disable requires_vote (should succeed)
        agenda.write({"requires_vote": False})
        self.assertFalse(agenda.requires_vote)

        # Can clear vote_type_id now
        agenda.write({"vote_type_id": False})
        self.assertFalse(agenda.vote_type_id)

    def test_agenda_vote_type_immutability_with_multiple_votings(self):
        """vote_type_id immutability when multiple votings exist."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        agenda = assembly.agenda_ids[0]
        vote_type = agenda.vote_type_id

        # Create another vote type in assembly
        other_vote_type = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        assembly.vote_type_ids = [(4, other_vote_type.id)]

        # One open voting per agenda item; immutability applies once any voting exists
        agenda.action_start_voting()
        self.assertEqual(len(agenda.voting_ids), 1)

        # Cannot change vote_type_id (votings exist)
        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"vote_type_id": other_vote_type.id})
        self.assertIn("cannot be changed", str(ctx.exception).lower())
        self.assertIn("already has votings", str(ctx.exception))

        # Original vote_type_id should remain
        self.assertEqual(agenda.vote_type_id, vote_type)

    def test_agenda_validation_with_empty_assembly_vote_types(self):
        """Agenda validation when assembly has no vote types."""
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

        # Create vote type
        vote_type = self._create_vote_type(self.env, name="VT", code="VT")
        # pylint: disable=protected-access
        # Cannot create agenda with requires_vote=True (no vote types in assembly)
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

        # Can create agenda with requires_vote=False
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Valid Agenda",
                "requires_vote": False,
                "vote_type_id": False,
            }
        )
        self.assertFalse(agenda.requires_vote)
        self.assertFalse(agenda.vote_type_id)

    def test_agenda_validation_concurrent_changes(self):
        """Agenda validation handles concurrent field changes correctly."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        agenda = assembly.agenda_ids[0]
        vote_type = agenda.vote_type_id

        # Create another vote type
        other_vote_type = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        assembly.vote_type_ids = [(4, other_vote_type.id)]

        # Try to change both requires_vote and vote_type_id together
        # Case 1: Set requires_vote=True and vote_type_id together (should succeed)
        agenda.write({"requires_vote": False, "vote_type_id": False})
        agenda.write({"requires_vote": True, "vote_type_id": vote_type.id})
        self.assertTrue(agenda.requires_vote)
        self.assertEqual(agenda.vote_type_id, vote_type)

        # Case 2: Try to set requires_vote=True and clear vote_type_id (should fail)
        agenda.write({"requires_vote": False, "vote_type_id": False})
        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"requires_vote": True, "vote_type_id": False})
        msg = str(ctx.exception).lower()
        self.assertIn("vote type", msg)
        self.assertIn("requires", msg)

    def test_agenda_validation_with_voting_in_progress(self):
        """Agenda validation when voting is in progress."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        agenda = assembly.agenda_ids[0]
        vote_type = agenda.vote_type_id  # noqa: F841

        # Start voting
        agenda.action_start_voting()
        self.assertEqual(agenda.agenda_state, "in_progress")
        self.assertTrue(agenda.voting_ids)

        # Create another vote type
        other_vote_type = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        assembly.vote_type_ids = [(4, other_vote_type.id)]

        # Cannot change vote_type_id (voting in progress)
        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"vote_type_id": other_vote_type.id})
        self.assertIn("cannot be changed", str(ctx.exception).lower())

        # Can change other fields (name, description)
        agenda.write({"name": "Updated Name"})
        self.assertEqual(agenda.name, "Updated Name")

        # Cannot clear vote_type_id (blocked like change: votings exist)
        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"vote_type_id": False})
        msg_clear = str(ctx.exception).lower()
        self.assertTrue(
            "cannot be cleared" in msg_clear or "cannot be changed" in msg_clear,
            msg_clear,
        )

    def test_agenda_multiple_agendas_different_vote_types(self):
        """Multiple agendas can use different vote types from same assembly."""
        vote_type1 = self._create_vote_type(self.env, name="VT1", code="VT1")
        # pylint: disable=protected-access
        vote_type2 = self._create_vote_type(self.env, name="VT2", code="VT2")
        # pylint: disable=protected-access
        assembly_type = self.env["assembly.type"].create(
            {
                "name": "Multi Type",
                "code": "MULTI",
                "vote_type_ids": [(6, 0, [vote_type1.id, vote_type2.id])],
                "default_quorum_type": "percentage",
                "default_quorum_value": 50.0,
                "default_quorum_second_call_type": "any",
                "default_quorum_second_call_value": 0.0,
                "partner_domain": "[]",
            }
        )
        assembly = self.env["assembly.assembly"].create(
            {
                "name": "Multi Type Assembly",
                "assembly_type_id": assembly_type.id,
            }
        )

        # Create multiple agendas with different vote types
        agenda1 = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Agenda 1",
                "requires_vote": True,
                "vote_type_id": vote_type1.id,
                "sequence": 10,
            }
        )
        agenda2 = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Agenda 2",
                "requires_vote": True,
                "vote_type_id": vote_type2.id,
                "sequence": 20,
            }
        )
        agenda3 = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Agenda 3",
                "requires_vote": True,
                "vote_type_id": vote_type1.id,  # Can reuse vote_type1
                "sequence": 30,
            }
        )

        # All should be valid
        self.assertEqual(agenda1.vote_type_id, vote_type1)
        self.assertEqual(agenda2.vote_type_id, vote_type2)
        self.assertEqual(agenda3.vote_type_id, vote_type1)

        # Each can start voting independently
        agenda1.action_start_voting()
        agenda2.action_start_voting()
        self.assertTrue(agenda1.voting_ids)
        self.assertTrue(agenda2.voting_ids)

        # agenda1 cannot change vote_type (has voting)
        with self.assertRaises(ValidationError):
            agenda1.write({"vote_type_id": vote_type2.id})

        # agenda3 can still change (no voting)
        agenda3.write({"vote_type_id": vote_type2.id})
        self.assertEqual(agenda3.vote_type_id, vote_type2)
