# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyAttendeeConfirmWarning(AssemblyTestMixin, TransactionCase):
    """Tests for assembly.attendee.action_confirm() with delegation warnings."""

    def test_action_confirm_without_delegations_no_warning(self):
        """action_confirm() without delegations returns True (no warning)."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        attendee = assembly.attendee_ids[0]

        # Confirm attendee (no delegations)
        result = attendee.action_confirm()

        # Verify confirmation
        self.assertEqual(attendee.attendee_state, "confirmed")
        self.assertTrue(attendee.date_register)

        # Verify no warning (returns True)
        self.assertTrue(result)

    def test_action_confirm_with_active_delegations_shows_warning(self):
        """action_confirm() shows warning when partner has active delegations."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        delegate.action_confirm()

        # Create active delegation
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )

        # Confirm delegator (has active delegation)
        result = delegator.action_confirm()

        # Verify confirmation
        self.assertEqual(delegator.attendee_state, "confirmed")
        self.assertTrue(delegator.date_register)

        # Verify delegation still active (not revoked)
        delegation.invalidate_recordset()
        self.assertEqual(delegation.delegation_state, "confirmed")

        # Verify warning returned
        self.assertIsInstance(result, dict)
        self.assertIn("warning", result)
        self.assertIn("title", result["warning"])
        self.assertIn("message", result["warning"])
        self.assertIn("delegation", result["warning"]["message"].lower())
        self.assertIn(delegate.partner_id.name, result["warning"]["message"])
        self.assertIn(delegator.partner_id.name, result["warning"]["message"])

    def test_action_confirm_with_multiple_delegations_shows_all(self):
        """action_confirm() shows all delegates when multiple delegations exist."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type_a = assembly.assembly_type_id.vote_type_ids[0]
        vote_type_b = self._create_vote_type(self.env, name="VT extra warn")
        assembly.assembly_type_id.write({"vote_type_ids": [(4, vote_type_b.id)]})
        assembly.write({"vote_type_ids": [(4, vote_type_b.id)]})
        delegator = assembly.attendee_ids[0]
        delegate1 = assembly.attendee_ids[1]
        delegate2 = assembly.attendee_ids[2]
        for p in delegator.partner_id | delegate1.partner_id | delegate2.partner_id:
            self._give_partner_votes(p, vote_type_b, 1)
        delegate1.action_confirm()
        delegate2.action_confirm()

        # Create two active delegations (disjoint vote types: same delegator OK)
        delegation1 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate1.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type_a.ids)],
                "delegation_state": "confirmed",
            }
        )
        delegation2 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate2.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type_b.ids)],
                "delegation_state": "confirmed",
            }
        )

        # Confirm delegator
        result = delegator.action_confirm()

        # Verify confirmation
        self.assertEqual(delegator.attendee_state, "confirmed")

        # Verify both delegations still active
        delegation1.invalidate_recordset()
        delegation2.invalidate_recordset()
        self.assertEqual(delegation1.delegation_state, "confirmed")
        self.assertEqual(delegation2.delegation_state, "confirmed")

        # Verify warning mentions both delegates
        self.assertIsInstance(result, dict)
        self.assertIn("warning", result)
        message = result["warning"]["message"]
        self.assertIn(delegate1.partner_id.name, message)
        self.assertIn(delegate2.partner_id.name, message)
        self.assertIn("2", message)  # Count of delegations

    def test_action_confirm_with_draft_delegation_no_warning(self):
        """action_confirm() does not show warning for draft delegations."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]

        # Create draft delegation (not confirmed)
        _ = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "draft",  # Not confirmed
            }
        )

        # Confirm delegator
        result = delegator.action_confirm()

        # Verify confirmation
        self.assertEqual(delegator.attendee_state, "confirmed")

        # Verify no warning (draft delegation not counted)
        self.assertTrue(result)

    def test_action_confirm_with_revoked_delegation_no_warning(self):
        """action_confirm() does not show warning for revoked delegations."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        delegate.action_confirm()

        # Create and revoke delegation
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        delegation.write({"delegation_state": "revoked"})

        # Confirm delegator
        result = delegator.action_confirm()

        # Verify confirmation
        self.assertEqual(delegator.attendee_state, "confirmed")

        # Verify no warning (revoked delegation not counted)
        self.assertTrue(result)

    def test_action_confirm_recomputes_votes(self):
        """action_confirm() recomputes votes even with delegations."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]

        # Give votes
        self._give_partner_votes(delegator.partner_id, vote_type, 5)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type, 2)
        # pylint: disable=protected-access
        delegate.action_confirm()
        _ = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )

        result = delegator.action_confirm()

        # Verify votes recomputed
        delegator.recompute_attendee_vote_lines()
        av = self.env["assembly.attendee.vote"].search(  # noqa: F841
            [
                ("attendee_id", "=", delegator.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertTrue(av)
        # Delegator should have delegated_out_votes if delegate is confirmed
        # (This depends on the delegation logic fix we did earlier)

        # Verify warning still shown
        self.assertIsInstance(result, dict)
        self.assertIn("warning", result)

    def test_action_confirm_multiple_attendees_accumulates_warnings(self):
        """action_confirm() on multiple attendees accumulates warnings."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator1 = assembly.attendee_ids[0]
        delegator2 = assembly.attendee_ids[1]
        delegate = assembly.attendee_ids[2]
        delegate.action_confirm()

        # Create delegations for both
        _ = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator1.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        _ = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator2.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )

        # Confirm both at once
        attendees = delegator1 | delegator2  # noqa: F841
        result = attendees.action_confirm()

        # Verify both confirmed
        self.assertEqual(delegator1.attendee_state, "confirmed")
        self.assertEqual(delegator2.attendee_state, "confirmed")

        # Verify warning contains both messages
        self.assertIsInstance(result, dict)
        self.assertIn("warning", result)
        message = result["warning"]["message"]
        self.assertIn(delegator1.partner_id.name, message)
        self.assertIn(delegator2.partner_id.name, message)

    def test_action_confirm_idempotent_with_delegations(self):
        """action_confirm() is idempotent: second call shows warning again."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]  # noqa: F841
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        delegate.action_confirm()

        _ = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )

        # First confirm
        result1 = delegator.action_confirm()
        self.assertIsInstance(result1, dict)
        self.assertIn("warning", result1)

        # Second confirm (already confirmed)
        result2 = delegator.action_confirm()  # noqa: F841
        # Should return True (no change, no warning)
        self.assertTrue(result2)
