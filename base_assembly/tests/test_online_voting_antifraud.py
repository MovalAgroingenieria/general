# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Antifraud and security tests for online voting: double vote, eligibility,
delegation, results, concurrency.

See doc/ONLINE_VOTING_SECURITY_MATRIX.md.
"""

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestOnlineVotingDoubleVote(AssemblyTestMixin, TransactionCase):
    """Double vote: second line rejected (UNIQUE + constraint)."""

    def test_double_vote_second_line_rejected(self):
        """Same (voting_id, attendee_id) twice: second create must fail."""
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
        voting = assembly.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att.id,
                "vote_option": "yes",
                "votes_applied": 1.0,
                "vote_channel": "online",
            }
        )
        with self.assertRaises(Exception) as ctx:
            with self.env.cr.savepoint():
                self.env["assembly.voting.line"].create(
                    {
                        "voting_id": voting.id,
                        "attendee_id": att.id,
                        "vote_option": "no",
                        "votes_applied": 1.0,
                        "vote_channel": "online",
                    }
                )
        exc = ctx.exception
        self.assertTrue(
            "only once" in str(exc).lower()
            or "unique" in str(exc).lower()
            or "duplicate" in str(exc).lower()
            or "duplicada" in str(exc).lower()
            or "llave" in str(exc).lower(),
            "Expected UNIQUE or 'only once' error: %s" % exc,
        )
        lines = self.env["assembly.voting.line"].search(
            [("voting_id", "=", voting.id), ("attendee_id", "=", att.id)]
        )
        self.assertEqual(len(lines), 1)


class TestOnlineVotingOutOfWindow(AssemblyTestMixin, TransactionCase):
    """Voting outside window: closed or cancelled."""

    def test_vote_when_voting_closed_rejected(self):
        """Create voting.line when voting_state is closed → ValidationError."""
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
        voting = assembly.env["assembly.voting"].search(
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

    def test_vote_when_voting_cancelled_rejected(self):
        """Create voting.line when voting_state is cancelled → ValidationError."""
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
        voting = assembly.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        voting.action_cancel()
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


class TestOnlineVotingEligibility(AssemblyTestMixin, TransactionCase):
    """Identidad no elegible: 0 votos, votes_applied incorrecto."""

    def test_zero_votes_attendee_cannot_cast(self):
        """Attendee with attendee_vote_total 0 cannot have a voting line."""
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
        voting = assembly.env["assembly.voting"].search(
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

    def test_votes_applied_must_match_attendee_total(self):
        """votes_applied different from attendee_vote_total → ValidationError."""
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
        voting = assembly.env["assembly.voting"].search(
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


class TestOnlineVotingDelegationChange(AssemblyTestMixin, TransactionCase):
    """Delegation change with vote open."""

    def test_delegation_change_after_vote_open_attendee_total_updated(self):
        """After confirming delegation, creating line with old votes_applied fails."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator, delegate = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 5)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type, 2)
        # pylint: disable=protected-access
        delegator.action_confirm()
        delegate.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        assembly.agenda_ids[0].action_start_voting()
        voting = assembly.env["assembly.voting"].search(
            [("agenda_id", "=", assembly.agenda_ids[0].id)], limit=1
        )
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()
        delegate.invalidate_recordset()
        new_total = delegate.attendee_vote_ids.filtered(  # noqa: F841
            lambda v: v.vote_type_id == vote_type
        ).attendee_vote_total
        self.assertEqual(new_total, 7.0)
        with self.assertRaises(ValidationError) as ctx:
            self.env["assembly.voting.line"].create(
                {
                    "voting_id": voting.id,
                    "attendee_id": delegate.id,
                    "vote_option": "yes",
                    "votes_applied": 2.0,
                }
            )
        self.assertIn("must match", str(ctx.exception))
        self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": delegate.id,
                "vote_option": "yes",
                "votes_applied": 7.0,
            }
        )

    def test_existing_line_unchanged_after_delegation_revoke(self):
        """After revoking delegation, existing voting.line keeps same votes_applied."""
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator, delegate = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 3)
        # pylint: disable=protected-access
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        # pylint: disable=protected-access
        delegator.action_confirm()
        delegate.action_confirm()
        delegation = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = assembly.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        line = self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": delegate.id,
                "vote_option": "yes",
                "votes_applied": 4.0,
                "vote_channel": "online",
            }
        )
        delegation.delegation_state = "revoked"
        delegator.recompute_attendee_vote_lines()
        delegate.recompute_attendee_vote_lines()
        line.invalidate_recordset()
        self.assertEqual(line.votes_applied, 4.0)
        self.assertEqual(voting.total_votes_cast, 4.0)


class TestOnlineVotingResultModification(AssemblyTestMixin, TransactionCase):
    """Subsequent modification of result."""

    def test_user_cannot_write_voting_result(self):
        """assembly_group_user cannot write assembly.voting.result."""
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
        voting = assembly.env["assembly.voting"].search(
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
        voting.action_close()
        result = voting.result_ids.filtered(lambda r: r.vote_option == "yes")[0]
        group_user = self.env.ref(
            "base_assembly.assembly_group_user", raise_if_not_found=False
        )
        if not group_user:
            self.skipTest("assembly_group_user not found")
        try:
            user = self.env["res.users"].create(  # noqa: F841
                {
                    "name": "Assembly User Antifraud",
                    "login": "antifraud_assembly_user",
                    "password": "antifraud_assembly_user",
                    "groups_id": [
                        (6, 0, [self.env.ref("base.group_user").id, group_user.id])
                    ],
                }
            )
        except Exception as e:
            if "calendar_default_privacy" in str(e) or "not null" in str(e).lower():
                self.skipTest("res.users.settings requires calendar_default_privacy")
            raise
        with self.assertRaises(AccessError):
            self.env["assembly.voting.result"].with_user(user).browse(result.id).write(
                {"total_votes": 999.0}
            )


class TestOnlineVotingConcurrency(AssemblyTestMixin, TransactionCase):
    """Unicidad (voting_id, attendee_id): segundo create rechazado."""

    def test_concurrent_double_vote_only_one_succeeds(self):
        """Second create with same (voting_id, attendee_id) must fail;
        exactly one line exists."""
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
        voting = assembly.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        vals = {
            "voting_id": voting.id,
            "attendee_id": att.id,
            "vote_option": "yes",
            "votes_applied": 1.0,
            "vote_channel": "online",
        }
        self.env["assembly.voting.line"].create(vals)
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.env["assembly.voting.line"].create(vals)
        lines = self.env["assembly.voting.line"].search(  # noqa: F841
            [("voting_id", "=", voting.id), ("attendee_id", "=", att.id)]
        )
        self.assertEqual(len(lines), 1, "Exactly one line must exist")


class TestOnlineVotingTokenPlaceholders(AssemblyTestMixin, TransactionCase):
    """Placeholders for token-based vote: reuse, revoked, expired (when model/control
    ler exist)."""

    def test_token_reuse_second_cast_rejected(self):
        """When voting token exists: second cast with same token must be rejected."""
        self.skipTest("Implement when assembly.voting.token and controller exist")

    def test_revoked_token_cannot_cast(self):
        """When voting token exists: revoked token must not allow cast."""
        self.skipTest("Implement when assembly.voting.token and revoke flow exist")

    def test_expired_token_cannot_cast(self):
        """When voting token exists: expired token must not allow cast."""
        self.skipTest("Implement when assembly.voting.token and expires_at exist")
