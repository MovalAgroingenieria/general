# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import uuid

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
            }
        )

        # Confirm delegator (has active delegation)
        result = delegator.action_confirm()

        # Verify confirmation happened anyway (business rule)
        self.assertEqual(delegator.attendee_state, "confirmed")
        self.assertTrue(delegator.date_register)

        delegation.invalidate_recordset()
        self.assertTrue(delegation.exists())

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
            "Voting units stay assigned",
            result["warning"]["message"],
        )
        self.assertIn(
            "delegation",
            result["warning"]["message"].lower(),
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
            }
        )
        delegation2 = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate2.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type_b.ids)],
            }
        )

        # Confirm delegator
        result = delegator.action_confirm()

        # Verify confirmation
        self.assertEqual(delegator.attendee_state, "confirmed")

        # Verify both delegations still active (NOT revoked)
        delegation1.invalidate_recordset()
        delegation2.invalidate_recordset()

        # Verify notification mentions both delegates
        self.assertIsInstance(result, dict)
        self.assertIn("warning", result)
        message = result["warning"]["message"]
        self.assertIn(delegate1.partner_id.name, message)
        self.assertIn(delegate2.partner_id.name, message)
        self.assertIn("2", message)  # Count of delegations

    def test_action_confirm_only_confirmed_delegations_notified(self):
        """action_confirm() warns only for effective outbound delegations.

        Ineffective rows (delegate not confirmed yet) and removed rows must not warn.
        """
        assembly_a, _ = self._create_assembly_with_agenda(
            name="Confirm notify A %s" % uuid.uuid4().hex[:8],
        )
        assembly_a.action_generate_attendees()
        vote_a = assembly_a.assembly_type_id.vote_type_ids[0]
        delegator_a = assembly_a.attendee_ids[0]
        delegate_a = assembly_a.attendee_ids[1]
        self._give_partner_votes(delegator_a.partner_id, vote_a, 1)
        self._give_partner_votes(delegate_a.partner_id, vote_a, 1)
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly_a.id,
                "partner_id": delegator_a.partner_id.id,
                "delegate_partner_id": delegate_a.partner_id.id,
                "vote_type_ids": [(6, 0, vote_a.ids)],
            }
        )
        result_a = delegator_a.action_confirm()
        self.assertEqual(delegator_a.attendee_state, "confirmed")
        self.assertTrue(
            result_a,
            "No warning while delegate is not confirmed (delegation not effective)",
        )
        self.assertNotIsInstance(result_a, dict)

        assembly_b, _ = self._create_assembly_with_agenda(
            name="Confirm notify B %s" % uuid.uuid4().hex[:8],
        )
        assembly_b.action_generate_attendees()
        vote_b = assembly_b.assembly_type_id.vote_type_ids[0]
        delegator_b = assembly_b.attendee_ids[0]
        delegate_b = assembly_b.attendee_ids[1]
        self._give_partner_votes(delegator_b.partner_id, vote_b, 1)
        self._give_partner_votes(delegate_b.partner_id, vote_b, 1)
        delegate_b.action_confirm()
        eff = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly_b.id,
                "partner_id": delegator_b.partner_id.id,
                "delegate_partner_id": delegate_b.partner_id.id,
                "vote_type_ids": [(6, 0, vote_b.ids)],
            }
        )
        eff.unlink()
        result_b = delegator_b.action_confirm()
        self.assertEqual(delegator_b.attendee_state, "confirmed")
        self.assertTrue(
            result_b,
            "No warning after effective delegation record was removed",
        )
        self.assertNotIsInstance(result_b, dict)

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
