# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestGeneralEntity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["res.partner"]
        cls.member_model = cls.env["general.entity.member"]

        cls.primary_entity = cls.partner_model.create(
            {
                "name": "Test Primary Entity",
                "is_primary_entity": True,
                "company_type": "company",
                "entity_global_code": 1001,
            }
        )
        cls.primary_entity_2 = cls.partner_model.create(
            {
                "name": "Test Primary Entity 2",
                "is_primary_entity": True,
                "company_type": "company",
                "entity_global_code": 1002,
            }
        )
        cls.secondary_member_1 = cls.partner_model.create(
            {
                "name": "Test Secondary Member 1",
                "is_secondary_entity": True,
                "company_type": "person",
                "entity_global_code": 2001,
            }
        )
        cls.secondary_member_2 = cls.partner_model.create(
            {
                "name": "Test Secondary Member 2",
                "is_secondary_entity": True,
                "company_type": "person",
                "entity_global_code": 2002,
            }
        )

    # ------------------------------------------------------------------
    # Constraint: a partner cannot be both primary and secondary
    # ------------------------------------------------------------------
    def test_exclusive_constraint_primary_to_secondary(self):
        """Cannot mark a primary entity as secondary member."""
        with self.assertRaises(ValidationError):
            self.primary_entity.write({"is_secondary_entity": True})

    def test_exclusive_constraint_secondary_to_primary(self):
        """Cannot mark a secondary member as primary entity."""
        with self.assertRaises(ValidationError):
            self.secondary_member_1.write({"is_primary_entity": True})

    # ------------------------------------------------------------------
    # Relationship creation and computed fields
    # ------------------------------------------------------------------
    def test_member_creation(self):
        """Create a relationship and verify related fields."""
        member = self.member_model.create(
            {
                "primary_partner_id": self.primary_entity.id,
                "member_partner_id": self.secondary_member_1.id,
                "member_code_in_entity": "M-001",
            }
        )
        self.assertTrue(member.id)
        self.assertEqual(member.entity_global_code, 2001)

    def test_member_count(self):
        """Member count is computed correctly."""
        self.member_model.create(
            {
                "primary_partner_id": self.primary_entity.id,
                "member_partner_id": self.secondary_member_1.id,
            }
        )
        self.member_model.create(
            {
                "primary_partner_id": self.primary_entity.id,
                "member_partner_id": self.secondary_member_2.id,
            }
        )
        self.primary_entity.invalidate_recordset()
        self.assertEqual(self.primary_entity.member_count, 2)

    # ------------------------------------------------------------------
    # Display name
    # ------------------------------------------------------------------
    def test_display_name_with_code(self):
        """Display name includes local code when set."""
        member = self.member_model.create(
            {
                "primary_partner_id": self.primary_entity.id,
                "member_partner_id": self.secondary_member_1.id,
                "member_code_in_entity": "M-01",
            }
        )
        expected = "[M-01] Test Primary Entity - Test Secondary Member 1"
        self.assertEqual(member.display_name, expected)

    def test_display_name_without_code(self):
        """Display name works without local code."""
        member = self.member_model.create(
            {
                "primary_partner_id": self.primary_entity.id,
                "member_partner_id": self.secondary_member_1.id,
            }
        )
        expected = "Test Primary Entity - Test Secondary Member 1"
        self.assertEqual(member.display_name, expected)

    # ------------------------------------------------------------------
    # Unique code within entity (Python constraint)
    # ------------------------------------------------------------------
    def test_unique_code_in_entity(self):
        """member_code_in_entity must be unique per primary entity."""
        self.member_model.create(
            {
                "primary_partner_id": self.primary_entity.id,
                "member_partner_id": self.secondary_member_1.id,
                "member_code_in_entity": "UNIQUE-01",
            }
        )
        with self.assertRaises(ValidationError):
            self.member_model.create(
                {
                    "primary_partner_id": self.primary_entity.id,
                    "member_partner_id": self.secondary_member_2.id,
                    "member_code_in_entity": "UNIQUE-01",
                }
            )

    def test_same_code_different_entities(self):
        """Same code is allowed in different primary entities."""
        self.member_model.create(
            {
                "primary_partner_id": self.primary_entity.id,
                "member_partner_id": self.secondary_member_1.id,
                "member_code_in_entity": "CODE-A",
            }
        )
        member_2 = self.member_model.create(
            {
                "primary_partner_id": self.primary_entity_2.id,
                "member_partner_id": self.secondary_member_1.id,
                "member_code_in_entity": "CODE-A",
            }
        )
        self.assertTrue(member_2.id)

    # ------------------------------------------------------------------
    # SQL unique constraint (primary + member + company)
    # ------------------------------------------------------------------
    def test_unique_sql_constraint(self):
        """Cannot duplicate relationship in same company."""
        self.member_model.create(
            {
                "primary_partner_id": self.primary_entity.id,
                "member_partner_id": self.secondary_member_1.id,
            }
        )
        with mute_logger("odoo.sql_db"):
            with self.assertRaises(Exception):
                self.member_model.create(
                    {
                        "primary_partner_id": self.primary_entity.id,
                        "member_partner_id": self.secondary_member_1.id,
                    }
                )

    # ------------------------------------------------------------------
    # Cascade delete: only removes relationships, NOT the other partner
    # ------------------------------------------------------------------
    def test_cascade_delete_primary_entity(self):
        """Deleting a primary entity removes relationships,
        but secondary member partners survive."""
        rel = self.member_model.create(
            {
                "primary_partner_id": self.primary_entity.id,
                "member_partner_id": self.secondary_member_1.id,
            }
        )
        rel_id = rel.id
        secondary_id = self.secondary_member_1.id

        self.primary_entity.unlink()

        # Relationship must be gone
        self.assertFalse(self.member_model.search([("id", "=", rel_id)]))
        # Secondary member must still exist
        self.assertTrue(self.partner_model.browse(secondary_id).exists())

    def test_cascade_delete_secondary_member(self):
        """Deleting a secondary member removes relationships,
        but primary entity partners survive."""
        rel = self.member_model.create(
            {
                "primary_partner_id": self.primary_entity.id,
                "member_partner_id": self.secondary_member_1.id,
            }
        )
        rel_id = rel.id
        primary_id = self.primary_entity.id

        self.secondary_member_1.unlink()

        # Relationship must be gone
        self.assertFalse(self.member_model.search([("id", "=", rel_id)]))
        # Primary entity must still exist
        self.assertTrue(self.partner_model.browse(primary_id).exists())

    # ------------------------------------------------------------------
    # Archive (active toggle)
    # ------------------------------------------------------------------
    def test_archive_relationship(self):
        """Archiving a relationship hides it but does not delete it."""
        rel = self.member_model.create(
            {
                "primary_partner_id": self.primary_entity.id,
                "member_partner_id": self.secondary_member_1.id,
            }
        )
        rel.write({"active": False})

        # Should not appear in default search (active=True)
        found = self.member_model.search(
            [
                ("primary_partner_id", "=", self.primary_entity.id),
                ("member_partner_id", "=", self.secondary_member_1.id),
            ]
        )
        self.assertFalse(found)

        # Should appear when including archived
        found_all = self.member_model.with_context(active_test=False).search(
            [
                ("primary_partner_id", "=", self.primary_entity.id),
                ("member_partner_id", "=", self.secondary_member_1.id),
            ]
        )
        self.assertTrue(found_all)

    # ------------------------------------------------------------------
    # action_view_members
    # ------------------------------------------------------------------
    def test_action_view_members(self):
        """action_view_members returns correct domain and context."""
        self.member_model.create(
            {
                "primary_partner_id": self.primary_entity.id,
                "member_partner_id": self.secondary_member_1.id,
            }
        )
        action = self.primary_entity.action_view_members()
        self.assertEqual(
            action["domain"],
            [("primary_partner_id", "=", self.primary_entity.id)],
        )
        self.assertEqual(
            action["context"]["default_primary_partner_id"],
            self.primary_entity.id,
        )


class TestPartnerEntityTypeWizard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["res.partner"]
        cls.wizard_model = cls.env["partner.entity.type.wizard"]

        cls.partner_1 = cls.partner_model.create({"name": "Wizard Test Partner 1"})
        cls.partner_2 = cls.partner_model.create({"name": "Wizard Test Partner 2"})

    def _run_wizard(self, action_type, partner_ids):
        """Helper to run the wizard with the given action and partners."""
        wizard = self.wizard_model.with_context(active_ids=partner_ids).create(
            {"action_type": action_type}
        )
        return wizard.action_apply()

    # ------------------------------------------------------------------
    # Mark / Unmark operations
    # ------------------------------------------------------------------
    def test_mark_primary(self):
        """Wizard marks selected partners as primary entities."""
        self._run_wizard(
            "mark_primary",
            [self.partner_1.id, self.partner_2.id],
        )
        self.assertTrue(self.partner_1.is_primary_entity)
        self.assertTrue(self.partner_2.is_primary_entity)

    def test_unmark_primary(self):
        """Wizard unmarks selected partners as primary entities."""
        self.partner_1.write({"is_primary_entity": True})
        self._run_wizard("unmark_primary", [self.partner_1.id])
        self.assertFalse(self.partner_1.is_primary_entity)

    def test_mark_secondary(self):
        """Wizard marks selected partners as secondary members."""
        self._run_wizard(
            "mark_secondary",
            [self.partner_1.id, self.partner_2.id],
        )
        self.assertTrue(self.partner_1.is_secondary_entity)
        self.assertTrue(self.partner_2.is_secondary_entity)

    def test_unmark_secondary(self):
        """Wizard unmarks selected partners as secondary members."""
        self.partner_1.write({"is_secondary_entity": True})
        self._run_wizard("unmark_secondary", [self.partner_1.id])
        self.assertFalse(self.partner_1.is_secondary_entity)

    def test_wizard_returns_close_action(self):
        """Wizard returns window close action."""
        result = self._run_wizard("mark_primary", [self.partner_1.id])
        self.assertEqual(result, {"type": "ir.actions.act_window_close"})

    # ------------------------------------------------------------------
    # Wizard conflict validation
    # ------------------------------------------------------------------
    def test_wizard_mark_primary_conflicts_with_secondary(self):
        """Wizard rejects marking secondary members as primary."""
        self.partner_1.write({"is_secondary_entity": True})
        with self.assertRaises(ValidationError):
            self._run_wizard(
                "mark_primary",
                [self.partner_1.id, self.partner_2.id],
            )
        # Ensure neither partner was modified
        self.assertFalse(self.partner_1.is_primary_entity)
        self.assertFalse(self.partner_2.is_primary_entity)

    def test_wizard_mark_secondary_conflicts_with_primary(self):
        """Wizard rejects marking primary entities as secondary."""
        self.partner_1.write({"is_primary_entity": True})
        with self.assertRaises(ValidationError):
            self._run_wizard(
                "mark_secondary",
                [self.partner_1.id, self.partner_2.id],
            )
        # Ensure neither partner was modified
        self.assertFalse(self.partner_1.is_secondary_entity)
        self.assertFalse(self.partner_2.is_secondary_entity)

    def test_wizard_unmark_no_conflict(self):
        """Unmark actions never conflict."""
        self.partner_1.write({"is_primary_entity": True})
        # Unmark primary on a primary entity should work fine
        result = self._run_wizard("unmark_primary", [self.partner_1.id])
        self.assertEqual(result, {"type": "ir.actions.act_window_close"})
        self.assertFalse(self.partner_1.is_primary_entity)
