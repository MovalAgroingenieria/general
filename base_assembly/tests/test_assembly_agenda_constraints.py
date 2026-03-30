# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyAgendaConstraints(AssemblyTestMixin, TransactionCase):
    """Tests for assembly.agenda constraints: vote_type_id requirements."""

    def test_vote_type_required_when_requires_vote_true(self):
        """vote_type_id is mandatory when requires_vote=True."""
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                agenda_title="Test agenda", requires_vote=True
            )
        )
        agenda = assembly.agenda_ids[0]
        # Initially vote_type_id is set by _create_assembly_with_agenda
        self.assertTrue(agenda.vote_type_id)

        # Try to remove vote_type_id when requires_vote=True
        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"vote_type_id": False})
        msg = str(ctx.exception).lower()
        self.assertIn("vote type", msg)
        self.assertTrue("require" in msg or "requires" in msg, msg)

    def test_vote_type_not_required_when_requires_vote_false(self):
        """No-vote mode has no vote type; vote type only after switching to weighted."""
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                agenda_title="Test agenda", requires_vote=False
            )
        )
        agenda = assembly.agenda_ids[0]
        self.assertEqual(agenda.agenda_vote_mode, "no_vote")
        agenda.write({"vote_type_id": False})
        self.assertFalse(agenda.vote_type_id)

        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        with self.assertRaises(ValidationError):
            agenda.write({"vote_type_id": vote_type.id})

        agenda.write({"agenda_vote_mode": "weighted", "vote_type_id": vote_type.id})
        self.assertEqual(agenda.vote_type_id, vote_type)
        self.assertEqual(agenda.agenda_vote_mode, "weighted")

    def test_vote_type_must_be_in_assembly_vote_type_ids(self):
        """vote_type_id must belong to assembly_id.vote_type_ids."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        agenda = assembly.agenda_ids[0]

        # Create a vote type not in the assembly
        other_vote_type = (
            self._create_vote_type(  # noqa: F841  # pylint: disable=protected-access
                self.env, name="Other type", code="OTHER"
            )
        )

        # Try to assign it
        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"vote_type_id": other_vote_type.id})
        self.assertIn("assembly's vote types", str(ctx.exception))

    def test_cannot_change_vote_type_when_votings_exist(self):
        """Cannot change vote_type_id if voting_ids already exist."""
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        vote_type1 = agenda.vote_type_id
        vote_type2 = assembly.assembly_type_id.vote_type_ids.filtered(
            lambda vt: vt != vote_type1
        )
        if not vote_type2:
            # Create a second vote type if needed
            vote_type2 = self._create_vote_type(self.env, name="VT2", code="VT2")
            # pylint: disable=protected-access
            assembly.write({"vote_type_ids": [(4, vote_type2.id)]})

        # Set initial vote type
        agenda.write({"vote_type_id": vote_type1.id})

        # Start voting (creates a voting)
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()

        # Verify voting exists
        self.assertTrue(agenda.voting_ids)

        # Try to change vote_type_id
        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"vote_type_id": vote_type2.id})
        self.assertIn("already has votings", str(ctx.exception))

    def test_can_change_vote_type_when_no_votings(self):
        """Can change vote_type_id if no voting_ids exist."""
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        vote_type1 = agenda.vote_type_id  # noqa: F841
        vote_type2 = assembly.assembly_type_id.vote_type_ids.filtered(
            lambda vt: vt != vote_type1
        )
        if not vote_type2:
            # Create a second vote type if needed
            vote_type2 = self._create_vote_type(self.env, name="VT2", code="VT2")
            # pylint: disable=protected-access
            assembly.write({"vote_type_ids": [(4, vote_type2.id)]})

        # Change vote_type_id (no votings exist yet)
        agenda.write({"vote_type_id": vote_type2.id})
        self.assertEqual(agenda.vote_type_id, vote_type2)

    def test_vote_type_required_on_create_when_requires_vote_true(self):
        """vote_type_id is required when creating agenda with requires_vote=True."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        vote_type = assembly.assembly_type_id.vote_type_ids[0]

        # Create agenda with requires_vote=True and vote_type_id
        agenda1 = self.env["assembly.agenda"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "name": "Agenda with vote type",
                "requires_vote": True,
                "vote_type_id": vote_type.id,
                "sequence": self._next_agenda_sequence(assembly),
            }
        )
        self.assertTrue(agenda1.vote_type_id)

        # Try to create agenda with requires_vote=True but no vote_type_id
        with self.assertRaises(ValidationError) as ctx:
            self.env["assembly.agenda"].create(
                {
                    "assembly_id": assembly.id,
                    "name": "Agenda without vote type",
                    "requires_vote": True,
                    "vote_type_id": False,
                    "sequence": self._next_agenda_sequence(assembly),
                }
            )
        msg = str(ctx.exception).lower()
        self.assertIn("vote type", msg)
        self.assertTrue("require" in msg or "requires" in msg, msg)

    def test_vote_type_not_required_on_create_when_requires_vote_false(self):
        """vote_type_id is optional when creating agenda with requires_vote=False."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access

        # Create agenda with requires_vote=False and no vote_type_id
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Agenda without vote",
                "requires_vote": False,
                "vote_type_id": False,
                "sequence": self._next_agenda_sequence(assembly),
            }
        )
        self.assertFalse(agenda.vote_type_id)
        self.assertFalse(agenda.requires_vote)

    def test_toggle_requires_vote_without_vote_type_raises(self):
        """requires_vote=True outside weighted mode is rejected."""
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

    def test_cannot_clear_vote_type_in_weighted_mode(self):
        """Clearing vote_type_id in weighted mode raises."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        agenda = assembly.agenda_ids[0]
        self.assertEqual(agenda.agenda_vote_mode, "weighted")
        with self.assertRaises(ValidationError) as ctx:
            agenda.write({"vote_type_id": False})
        msg = str(ctx.exception).lower()
        self.assertTrue("vote type" in msg or "cleared" in msg, msg)

    def test_toggle_requires_vote_with_vote_type_succeeds(self):
        """Switching from no-vote to weighted with vote type succeeds."""
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
