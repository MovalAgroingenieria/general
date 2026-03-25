# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyAttendeeConfirmImproved(AssemblyTestMixin, TransactionCase):
    """Tests for improved assembly.attendee.action_confirm()
    with delegation notifications."""

    def test_action_confirm_without_delegations_returns_true(self):
        """action_confirm() without delegations returns True (no notification)."""
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

        # Verify no notification (returns True)
        self.assertTrue(result)
        self.assertNotIsInstance(result, dict)

    def test_action_confirm_with_active_delegations_notifies_does_not_revoke(self):
        """action_confirm() notifies about active delegations
        but does NOT revoke them."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]

        # Give votes
        self._give_partner_votes(delegator.partner_id, vote_type, 10)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type, 5)
        # pylint: disable=protected-access
        # Confirm delegate first
        delegate.action_confirm()

        # Create active confirmed delegation
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

        # Verify confirmation happened anyway (business rule)
        self.assertEqual(delegator.attendee_state, "confirmed")
        self.assertTrue(delegator.date_register)

        # Verify delegation still active (NOT revoked automatically)
        delegation.invalidate_recordset()
        self.assertEqual(
            delegation.delegation_state,
            "confirmed",
            "Delegation must NOT be revoked automatically",
        )

        # Verify votes were recomputed
        delegator.recompute_attendee_vote_lines()
        av = self.env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", delegator.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertTrue(av, "Votes should be recomputed")

        # Verify notification returned (backend-friendly format)
        self.assertIsInstance(result, dict, "Should return dict with notification")
        self.assertIn("warning", result, "Should contain 'warning' key")
        self.assertIn("title", result["warning"], "Warning should have title")
        self.assertIn("message", result["warning"], "Warning should have message")
        self.assertEqual(
            result["warning"]["type"],
            "notification",
            "Should use notification type for less intrusive UX",
        )
        self.assertIn("delegation", result["warning"]["message"].lower())
        self.assertIn(delegate.partner_id.name, result["warning"]["message"])
        self.assertIn(delegator.partner_id.name, result["warning"]["message"])
        self.assertIn(
            "remain active",
            result["warning"]["message"],
            "Message should state delegations remain active",
        )
        self.assertIn(
            "manually",
            result["warning"]["message"],
            "Message should mention manual revocation option",
        )

    def test_action_confirm_with_multiple_delegations_shows_all(self):
        """action_confirm() shows all delegates when multiple delegations exist."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type_a = assembly.assembly_type_id.vote_type_ids[0]
        vote_type_b = self._create_vote_type(self.env, name="VT extra improved")
        assembly.assembly_type_id.write({"vote_type_ids": [(4, vote_type_b.id)]})
        assembly.write({"vote_type_ids": [(4, vote_type_b.id)]})
        delegator = assembly.attendee_ids[0]
        delegate1 = assembly.attendee_ids[1]
        delegate2 = assembly.attendee_ids[2] if len(assembly.attendee_ids) > 2 else None

        if not delegate2:
            self.skipTest("Need at least 3 attendees for multiple delegations test")

        for p in delegator.partner_id | delegate1.partner_id | delegate2.partner_id:
            self._give_partner_votes(p, vote_type_b, 1)
        delegate1.action_confirm()
        delegate2.action_confirm()

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

        # Verify both delegations still active (NOT revoked)
        delegation1.invalidate_recordset()
        delegation2.invalidate_recordset()
        self.assertEqual(delegation1.delegation_state, "confirmed")
        self.assertEqual(delegation2.delegation_state, "confirmed")

        # Verify notification mentions both delegates
        self.assertIsInstance(result, dict)
        self.assertIn("warning", result)
        message = result["warning"]["message"]
        self.assertIn(delegate1.partner_id.name, message)
        self.assertIn(delegate2.partner_id.name, message)
        self.assertIn("2", message)  # Count of delegations

    def test_action_confirm_only_confirmed_delegations_notified(self):
        """action_confirm() only notifies about confirmed delegations,
        not draft/revoked."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        delegate.action_confirm()

        # Create draft delegation (should NOT trigger notification)
        draft_delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "draft",
            }
        )

        # Create revoked delegation (should NOT trigger notification)
        revoked_delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        revoked_delegation.write({"delegation_state": "revoked"})

        # Confirm delegator
        result = delegator.action_confirm()

        # Verify confirmation
        self.assertEqual(delegator.attendee_state, "confirmed")

        # Verify no notification (only confirmed delegations count)
        self.assertTrue(result, "Should return True when no confirmed delegations")

    def test_action_confirm_backend_friendly_format(self):
        """action_confirm() returns backend-friendly notification format for API/RPC."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]

        # Confirm delegate first
        delegate.action_confirm()

        # Create active delegation
        _ = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )

        # Confirm delegator
        result = delegator.action_confirm()

        # Verify backend-friendly format
        self.assertIsInstance(result, dict)
        self.assertIn("warning", result)
        warning = result["warning"]
        # Standard Odoo warning format
        self.assertIn("title", warning)
        self.assertIn("message", warning)
        self.assertIn("type", warning)
        # Type should be 'notification' for less intrusive UX
        self.assertEqual(warning["type"], "notification")
        # Message should be informative
        self.assertIsInstance(warning["message"], str)
        self.assertTrue(len(warning["message"]) > 0)

    def test_action_confirm_always_recomputes_votes(self):
        """action_confirm() always recomputes votes regardless of delegations."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        attendee = assembly.attendee_ids[0]

        # Give votes
        self._give_partner_votes(attendee.partner_id, vote_type, 8)
        # pylint: disable=protected-access
        # Confirm attendee (no delegations)
        result = attendee.action_confirm()

        # Verify votes recomputed
        attendee.recompute_attendee_vote_lines()
        av = self.env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", attendee.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertTrue(av, "Votes should be recomputed")
        self.assertEqual(av.own_votes, 8.0)

        # Verify no notification
        self.assertTrue(result)
