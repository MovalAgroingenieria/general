# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
# pylint: disable=invalid-name

"""Security tests: ACLs and record rules for base_assembly.

Validates that:
- Users without assembly group cannot access assembly models.
- assembly_group_user: read + write own ``assembly.attendee`` (AF §8); create own
  ``assembly.delegation`` (draft); record rules scope rows; may create own
<<<<<<< HEAD
  ``assembly.voting.line``; representation rows only when owner/agent matches
  partner; cannot write assembly/agenda/voting/result or run manager-only actions.
=======
  ``assembly.voting.line``; cannot write assembly/agenda/voting/result or run
  manager-only actions.
>>>>>>> origin/18.0
- assembly_group_manager has full access.
"""

import unittest

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblySecurityACL(  # pylint: disable=too-many-public-methods
    AssemblyTestMixin, TransactionCase
):
    """ACL and record rule security tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref("base_assembly.assembly_group_user")
        cls.group_manager = cls.env.ref("base_assembly.assembly_group_manager")
        cls.base_user = cls.env.ref("base.group_user")

        try:
<<<<<<< HEAD
            cid = cls.env.company.id
=======
>>>>>>> origin/18.0
            cls.user_no_assembly = cls.env["res.users"].create(
                {
                    "name": "User No Assembly",
                    "login": "user_no_assembly_sec",
                    "password": "user_no_assembly_sec",
<<<<<<< HEAD
                    "company_id": cid,
                    "company_ids": [(6, 0, [cid])],
=======
>>>>>>> origin/18.0
                    "groups_id": [(6, 0, [cls.base_user.id])],
                }
            )
            cls.user_assembly_user = cls.env["res.users"].create(
                {
                    "name": "Assembly User",
                    "login": "assembly_user_sec",
                    "password": "assembly_user_sec",
<<<<<<< HEAD
                    "company_id": cid,
                    "company_ids": [(6, 0, [cid])],
=======
>>>>>>> origin/18.0
                    "groups_id": [(6, 0, [cls.base_user.id, cls.group_user.id])],
                }
            )
            cls.user_assembly_manager = cls.env["res.users"].create(
                {
                    "name": "Assembly Manager",
                    "login": "assembly_manager_sec",
                    "password": "assembly_manager_sec",
<<<<<<< HEAD
                    "company_id": cid,
                    "company_ids": [(6, 0, [cid])],
=======
>>>>>>> origin/18.0
                    "groups_id": [(6, 0, [cls.base_user.id, cls.group_manager.id])],
                }
            )
        except Exception as e:
            if "calendar_default_privacy" in str(e) or "not null" in str(e).lower():
                raise unittest.SkipTest(
                    "res.users.settings requires calendar_default_privacy "
                    "(e.g. calendar module)"
                ) from e
            raise

    # --- SEC-ACL-01: user without assembly group cannot read ---

    def test_user_without_assembly_group_cannot_read_assembly(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        env = self.env(user=self.user_no_assembly)
        with self.assertRaises(AccessError):
            env["assembly.assembly"].browse(assembly.id).read(["name"])

    def test_user_without_assembly_group_cannot_search_assembly(self):
        self._create_assembly_with_agenda()  # pylint: disable=protected-access
        env = self.env(user=self.user_no_assembly)
        with self.assertRaises(AccessError):
            env["assembly.assembly"].search([])

    def test_user_without_assembly_group_cannot_read_attendee(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        attendee = assembly.attendee_ids[0]
        env = self.env(user=self.user_no_assembly)
        with self.assertRaises(AccessError):
            env["assembly.attendee"].browse(attendee.id).read(["partner_id"])

    # --- SEC-ACL-02 / SEC-ACT-01: assembly user cannot write assembly or close ---

    def test_assembly_user_cannot_write_assembly(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        env = self.env(user=self.user_assembly_user)
        with self.assertRaises(AccessError):
            env["assembly.assembly"].browse(assembly.id).write({"name": "Hacked"})

    def test_assembly_user_cannot_close_assembly(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_skip()
        env = self.env(user=self.user_assembly_user)
        with self.assertRaises(AccessError):
            env["assembly.assembly"].browse(assembly.id).action_close()

    def test_assembly_user_cannot_announce_assembly(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        env = self.env(user=self.user_assembly_user)
        with self.assertRaises(AccessError):
            env["assembly.assembly"].browse(assembly.id).action_announce()

    def test_assembly_user_cannot_open_registration(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_announce()
        env = self.env(user=self.user_assembly_user)
        with self.assertRaises(AccessError):
            env["assembly.assembly"].browse(assembly.id).action_open_registration()

    def test_assembly_user_cannot_start_session(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_announce()
        assembly.action_open_registration()
        env = self.env(user=self.user_assembly_user)
        with self.assertRaises(AccessError):
            env["assembly.assembly"].browse(assembly.id).action_start_session()

    def test_assembly_user_cannot_generate_attendees(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        env = self.env(user=self.user_assembly_user)
        with self.assertRaises(AccessError):
            env["assembly.assembly"].browse(assembly.id).action_generate_attendees()

    # --- SEC-ACL-03: assembly user cannot create/edit type, agenda, voting, result ---

    def test_assembly_user_cannot_create_assembly_type(self):
        vote_type = self._create_vote_type(self.env)  # pylint: disable=protected-access
        env = self.env(user=self.user_assembly_user)
        with self.assertRaises(AccessError):
            env["assembly.type"].create(
                {
                    "name": "T",
                    "code": "T",
                    "vote_type_ids": [(6, 0, vote_type.ids)],
                }
            )

    def test_assembly_user_cannot_write_assembly_type(self):
        atype = self._create_assembly_type(  # noqa: F841
            self.env
        )  # pylint: disable=protected-access
        env = self.env(user=self.user_assembly_user)
        with self.assertRaises(AccessError):
            env["assembly.type"].browse(atype.id).write({"name": "Hacked"})

    def test_assembly_user_cannot_create_agenda(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        env = self.env(user=self.user_assembly_user)
        with self.assertRaises(AccessError):
            env["assembly.agenda"].create(
                {"assembly_id": assembly.id, "name": "Point 2", "requires_vote": False}
            )

    def test_assembly_user_cannot_write_voting(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        env = self.env(user=self.user_assembly_user)
        with self.assertRaises(AccessError):
            env["assembly.voting"].browse(voting.id).write(
                {"voting_state": "cancelled"}
            )

    def test_assembly_user_cannot_close_voting(self):
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
        voting = self.env["assembly.voting"].search(
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
        env = self.env(user=self.user_assembly_user)
        with self.assertRaises(AccessError):
            env["assembly.voting"].browse(voting.id).action_close()

    # --- SEC-ACL-04: assembly user cannot unlink attendee, delegation, voting.line ---

    def test_assembly_user_cannot_create_attendee(self):
        """Attendees are created by managers (generate attendees), not assembly users."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        env = self.env(user=self.user_assembly_user)
        with self.assertRaises(AccessError):
            env["assembly.attendee"].create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": self.user_assembly_user.partner_id.id,
                }
            )

    def test_assembly_user_cannot_unlink_attendee(self):
        partner = self.user_assembly_user.partner_id
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                partner_domain="[('id', '=', %s)]" % partner.id
            )
        )
        assembly.action_generate_attendees()
        attendee_own = assembly.attendee_ids.filtered(lambda a: a.partner_id == partner)
        self.assertTrue(attendee_own)
        env = self.env(user=self.user_assembly_user)
        with self.assertRaises(AccessError):
            env["assembly.attendee"].browse(attendee_own.id).unlink()

    def test_assembly_user_cannot_unlink_voting_line(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self.user_assembly_user.partner_id = att.partner_id
        self._give_partner_votes(
            att.partner_id, vote_type, 1
        )  # pylint: disable=protected-access
        att.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        line = self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att.id,
                "vote_option": "yes",
                "votes_applied": 1.0,
            }
        )
        env = self.env(user=self.user_assembly_user)
        with self.assertRaises(AccessError):
            env["assembly.voting.line"].browse(line.id).unlink()

    # --- SEC-ACL-05: manager full access (smoke) ---

    def test_assembly_manager_can_read_and_write_assembly(self):
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        env = self.env(user=self.user_assembly_manager)
        a = env["assembly.assembly"].browse(assembly.id)
        a.read(["name", "assembly_state"])
        a.write({"name": "Renamed by manager"})
        self.assertEqual(a.name, "Renamed by manager")

    def test_assembly_manager_can_close_assembly(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_skip()
        env = self.env(user=self.user_assembly_manager)
        env["assembly.assembly"].browse(assembly.id).action_close()
        self.assertEqual(assembly.assembly_state, "closed")

    # --- SEC-RR-01..04: record rules: user sees only own attendee, delegation,
    # representation, voting.line ---

    def test_assembly_user_sees_only_own_attendees(self):
        partners = self._create_partners(
            self.env, 3
        )  # pylint: disable=protected-access
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                partner_domain="[('id', 'in', %s)]" % partners.ids
            )
        )
        assembly.action_generate_attendees()
        self.user_assembly_user.partner_id = partners[0]
        env = self.env(user=self.user_assembly_user)
        attendees = env["assembly.attendee"].search([("assembly_id", "=", assembly.id)])
        self.assertEqual(len(attendees), 1)
        self.assertEqual(attendees.partner_id, partners[0])

    def test_assembly_user_cannot_read_other_partner_attendee(self):
        partners = self._create_partners(
            self.env, 2
        )  # pylint: disable=protected-access
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                partner_domain="[('id', 'in', %s)]" % partners.ids
            )
        )
        assembly.action_generate_attendees()
        attendee_other = assembly.attendee_ids.filtered(
            lambda a: a.partner_id == partners[1]
        )
        self.user_assembly_user.partner_id = partners[0]
        env = self.env(user=self.user_assembly_user)
        found = env["assembly.attendee"].search([("id", "=", attendee_other.id)])
        self.assertFalse(found)

    def test_assembly_user_sees_only_own_delegations(self):
        partners = self._create_partners(
            self.env, 3
        )  # pylint: disable=protected-access
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                partner_domain="[('id', 'in', %s)]" % partners.ids
            )
        )
        assembly.action_generate_attendees()
        assembly.action_announce()
        assembly.action_open_registration()
        delegation_own = self.env["assembly.delegation"].create(  # noqa: F841
            {
                "assembly_id": assembly.id,
                "partner_id": partners[0].id,
                "delegate_partner_id": partners[1].id,
                "vote_type_ids": [(6, 0, assembly.assembly_type_id.vote_type_ids.ids)],
            }
        )
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": partners[1].id,
                "delegate_partner_id": partners[2].id,
                "vote_type_ids": [(6, 0, assembly.assembly_type_id.vote_type_ids.ids)],
            }
        )
        self.user_assembly_user.partner_id = partners[0]
        env = self.env(user=self.user_assembly_user)
        delegations = env["assembly.delegation"].search(
            [("assembly_id", "=", assembly.id)]
        )
        self.assertEqual(len(delegations), 1)
        self.assertEqual(delegations[0].id, delegation_own.id)

    def test_assembly_user_cannot_write_other_partner_delegation(self):
        partners = self._create_partners(
            self.env, 2
        )  # pylint: disable=protected-access
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                partner_domain="[('id', 'in', %s)]" % partners.ids
            )
        )
        assembly.action_generate_attendees()
        assembly.action_announce()
        assembly.action_open_registration()
        delegation_other = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": partners[1].id,
                "delegate_partner_id": partners[0].id,
                "vote_type_ids": [(6, 0, assembly.assembly_type_id.vote_type_ids.ids)],
            }
        )
        self.user_assembly_user.partner_id = partners[0]
        env = self.env(user=self.user_assembly_user)
        self.assertFalse(
            env["assembly.delegation"].search([("id", "=", delegation_other.id)])
        )
        with self.assertRaises(AccessError):
            env["assembly.delegation"].browse(delegation_other.id).write(
                {"delegation_state": "confirmed"}
            )

<<<<<<< HEAD
    def test_assembly_user_sees_representations_as_owner_or_agent_only(self):
        partners = self._create_partners(
            self.env, 4, prefix="RepSec"
        )  # pylint: disable=protected-access
        domain = "[('id', 'in', %s)]" % partners.ids
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                partner_domain=domain
            )
        )
        rep_model = self.env["assembly.representation"]
        row_own = rep_model.create(
            {
                "assembly_id": assembly.id,
                "owner_partner_id": partners[0].id,
                "agent_partner_id": partners[1].id,
            }
        )
        rep_model.create(
            {
                "assembly_id": assembly.id,
                "owner_partner_id": partners[2].id,
                "agent_partner_id": partners[3].id,
            }
        )
        self.user_assembly_user.partner_id = partners[0]
        env = self.env(user=self.user_assembly_user)
        found = env["assembly.representation"].search(
            [("assembly_id", "=", assembly.id)]
        )
        self.assertEqual(len(found), 1)
        self.assertEqual(found.id, row_own.id)

    def test_assembly_user_sees_representation_when_agent(self):
        partners = self._create_partners(
            self.env, 3, prefix="RepAg"
        )  # pylint: disable=protected-access
        domain = "[('id', 'in', %s)]" % partners.ids
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                partner_domain=domain
            )
        )
        row = self.env["assembly.representation"].create(
            {
                "assembly_id": assembly.id,
                "owner_partner_id": partners[0].id,
                "agent_partner_id": partners[1].id,
            }
        )
        self.user_assembly_user.partner_id = partners[1]
        env = self.env(user=self.user_assembly_user)
        self.assertTrue(
            env["assembly.representation"].search([("id", "=", row.id)], limit=1)
        )

=======
>>>>>>> origin/18.0
    def test_assembly_user_sees_only_own_voting_lines(self):
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att1, att2 = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(
            att1.partner_id, vote_type, 1
        )  # pylint: disable=protected-access
        self._give_partner_votes(
            att2.partner_id, vote_type, 1
        )  # pylint: disable=protected-access
        att1.action_confirm()
        att2.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att1.id,
                "vote_option": "yes",
                "votes_applied": 1.0,
            }
        )
        self.env["assembly.voting.line"].create(
            {
                "voting_id": voting.id,
                "attendee_id": att2.id,
                "vote_option": "no",
                "votes_applied": 1.0,
            }
        )
        self.user_assembly_user.partner_id = att1.partner_id
        env = self.env(user=self.user_assembly_user)
        lines = env["assembly.voting.line"].search([("voting_id", "=", voting.id)])
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.attendee_id.partner_id, att1.partner_id)

    # --- SEC-RR-05: create voting.line for another attendee: hidden from user
    # (record rule) ---

    def test_assembly_user_create_voting_line_for_other_attendee_not_visible(self):
        """User creates voting.line with other's attendee_id:
        record rule hides it from him."""
        assembly, agenda = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att_own = assembly.attendee_ids[0]
        att_other = assembly.attendee_ids[1]
        self._give_partner_votes(att_own.partner_id, vote_type, 1)
        # pylint: disable=protected-access
        self._give_partner_votes(att_other.partner_id, vote_type, 1)
        # pylint: disable=protected-access
        att_own.action_confirm()
        att_other.action_confirm()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        self.user_assembly_user.partner_id = att_own.partner_id
        env = self.env(user=self.user_assembly_user)
        line_vals = {
            "voting_id": voting.id,
            "attendee_id": att_other.id,
            "vote_option": "yes",
            "votes_applied": 1.0,
        }
        with self.assertRaises(AccessError):
            env["assembly.voting.line"].create(line_vals)

    # --- SEC-ACT-05: user cannot confirm another partner's attendee (sees only own) ---

    def test_assembly_user_cannot_confirm_other_attendee(self):
        partners = self._create_partners(
            self.env, 2
        )  # pylint: disable=protected-access
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                partner_domain="[('id', 'in', %s)]" % partners.ids
            )
        )
        assembly.action_generate_attendees()
        assembly.action_announce()
        assembly.action_open_registration()
        attendee_other = assembly.attendee_ids.filtered(  # noqa: F841
            lambda a: a.partner_id == partners[1]
        )
        self.user_assembly_user.partner_id = partners[0]
        env = self.env(user=self.user_assembly_user)
        with self.assertRaises(AccessError):
            env["assembly.attendee"].browse(attendee_other.id).action_confirm()

    def test_assembly_user_can_confirm_own_attendance(self):
        """AF §8: assembly_group_user may write own attendee; confirm uses controlled write."""
        partner = self.user_assembly_user.partner_id
        assembly, _ = self._create_assembly_with_agenda(
            partner_domain="[('id', '=', %s)]" % partner.id
        )
        assembly.action_generate_attendees()
        att = assembly.attendee_ids.filtered(lambda a: a.partner_id == partner)
        self.assertTrue(att)
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        self._give_partner_votes(partner, vote_type, 1.0)
        env = self.env(user=self.user_assembly_user)
        env["assembly.attendee"].browse(att.id).action_confirm()
        self.assertEqual(att.sudo().attendee_state, "confirmed")

    def test_assembly_user_can_create_own_draft_delegation(self):
        """AF §8: assembly_group_user may create own delegation (draft)."""
        partners = self._create_partners(self.env, 2)
        self.user_assembly_user.partner_id = partners[0]
        assembly, _ = self._create_assembly_with_agenda(
            partner_domain="[('id', 'in', %s)]" % partners.ids
        )
        assembly.action_generate_attendees()
        env = self.env(user=self.user_assembly_user)
        rec = env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": partners[0].id,
                "delegate_partner_id": partners[1].id,
                "delegation_state": "draft",
            }
        )
        self.assertTrue(rec.id)
        self.assertEqual(rec.delegation_state, "draft")

    # --- SEC-DATA-01/02: read/write other partner's record ---

    def test_assembly_user_read_attendee_by_id_other_partner_returns_empty(self):
        partners = self._create_partners(
            self.env, 2
        )  # pylint: disable=protected-access
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                partner_domain="[('id', 'in', %s)]" % partners.ids
            )
        )
        assembly.action_generate_attendees()
        attendee_b = assembly.attendee_ids.filtered(  # noqa: F841
            lambda a: a.partner_id == partners[1]
        )
        self.user_assembly_user.partner_id = partners[0]
        env = self.env(user=self.user_assembly_user)
        self.assertFalse(env["assembly.attendee"].search([("id", "=", attendee_b.id)]))
<<<<<<< HEAD


class TestAssemblySecurityRegression(AssemblyTestMixin, TransactionCase):
    """Short ACL matrix: create/write/unlink smoke (complements TestAssemblySecurityACL)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref("base_assembly.assembly_group_user")
        cls.group_manager = cls.env.ref("base_assembly.assembly_group_manager")
        cls.base_user = cls.env.ref("base.group_user")
        try:
            cid = cls.env.company.id
            cls.user_assembly_user = cls.env["res.users"].create(
                {
                    "name": "Assembly User Reg",
                    "login": "assembly_user_reg",
                    "password": "assembly_user_reg",
                    "company_id": cid,
                    "company_ids": [(6, 0, [cid])],
                    "groups_id": [(6, 0, [cls.base_user.id, cls.group_user.id])],
                }
            )
            cls.user_assembly_manager = cls.env["res.users"].create(
                {
                    "name": "Assembly Manager Reg",
                    "login": "assembly_manager_reg",
                    "password": "assembly_manager_reg",
                    "company_id": cid,
                    "company_ids": [(6, 0, [cid])],
                    "groups_id": [(6, 0, [cls.base_user.id, cls.group_manager.id])],
                }
            )
        except Exception as e:
            if "calendar_default_privacy" in str(e) or "not null" in str(e).lower():
                raise unittest.SkipTest(
                    "res.users.settings requires calendar_default_privacy"
                ) from e
            raise

    def _env_user(self):
        return self.env(user=self.user_assembly_user)

    def _env_manager(self):
        return self.env(user=self.user_assembly_manager)

    def test_restricted_cannot_create_assembly(self):
        """ACL: Assembly User has no ``perm_create`` on ``assembly.assembly``."""
        atype = self._create_assembly_type(self.env)  # pylint: disable=protected-access
        with self.assertRaises(AccessError):
            self._env_user()["assembly.assembly"].create(
                {
                    "name": "Illegal assembly",
                    "assembly_type_id": atype.id,
                }
            )

    def test_restricted_cannot_unlink_assembly(self):
        """ACL: cannot delete assemblies without manager rights."""
        assembly, _ = (
            self._create_assembly_with_agenda()
        )  # pylint: disable=protected-access
        with self.assertRaises(AccessError):
            self._env_user()["assembly.assembly"].browse(assembly.id).unlink()

    def test_restricted_can_write_notes_on_own_attendee(self):
        """ACL: assembly user may write safe fields on own attendee (AF §8)."""
        partner = self.user_assembly_user.partner_id
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                partner_domain="[('id', '=', %s)]" % partner.id
            )
        )
        assembly.action_generate_attendees()
        attendee = assembly.attendee_ids.filtered(lambda a: a.partner_id == partner)
        self.assertTrue(attendee)
        self._env_user()["assembly.attendee"].browse(attendee.id).write(
            {"attendance_notes": "allowed"}
        )
        self.assertEqual(attendee.sudo().attendance_notes, "allowed")

    def test_restricted_cannot_create_delegation_as_other_delegator(self):
        """ACL: cannot create a delegation where delegator is another partner."""
        partners = self._create_partners(
            self.env, 2
        )  # pylint: disable=protected-access
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                partner_domain="[('id', 'in', %s)]" % partners.ids
            )
        )
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        self.user_assembly_user.partner_id = partners[0]
        with self.assertRaises(AccessError):
            self._env_user()["assembly.delegation"].create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": partners[1].id,
                    "delegate_partner_id": partners[0].id,
                    "vote_type_ids": [(6, 0, vt.ids)],
                    "delegation_state": "draft",
                }
            )

    def test_restricted_cannot_unlink_visible_delegation(self):
        """ACL: cannot unlink own delegation row even when visible via record rule."""
        partners = self._create_partners(
            self.env, 2
        )  # pylint: disable=protected-access
        assembly, _ = (
            self._create_assembly_with_agenda(  # pylint: disable=protected-access
                partner_domain="[('id', 'in', %s)]" % partners.ids
            )
        )
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        del_rec = self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": partners[0].id,
                "delegate_partner_id": partners[1].id,
                "vote_type_ids": [(6, 0, vt.ids)],
            }
        )
        self.user_assembly_user.partner_id = partners[0]
        env_u = self._env_user()
        self.assertTrue(env_u["assembly.delegation"].search([("id", "=", del_rec.id)]))
        with self.assertRaises(AccessError):
            env_u["assembly.delegation"].browse(del_rec.id).unlink()

    def test_manager_crud_smoke_assembly_attendee_delegation(self):
        """Manager ACL: create assembly, touch attendee, delegation lifecycle, cleanup."""
        env_m = self._env_manager()
        atype = self._create_assembly_type(self.env)  # pylint: disable=protected-access
        partners = self._create_partners(
            self.env, 2
        )  # pylint: disable=protected-access
        asm = env_m["assembly.assembly"].create(
            {
                "name": "Mgr regression asm",
                "assembly_type_id": atype.id,
                "partner_domain": "[('id', 'in', %s)]" % partners.ids,
            }
        )
        if atype.vote_type_ids and not asm.vote_type_ids:
            asm.write({"vote_type_ids": [(6, 0, atype.vote_type_ids.ids)]})
        asm.write({"name": "Mgr regression asm (updated)"})
        env_m["assembly.assembly"].browse(asm.id).action_generate_attendees()
        attendee = env_m["assembly.attendee"].search(
            [("assembly_id", "=", asm.id)], limit=1
        )
        self.assertTrue(attendee)
        attendee.write({"attendance_notes": "manager ok"})
        vt = asm.vote_type_ids[0]
        del_rec = env_m["assembly.delegation"].create(
            {
                "assembly_id": asm.id,
                "partner_id": partners[0].id,
                "delegate_partner_id": partners[1].id,
                "vote_type_ids": [(6, 0, vt.ids)],
            }
        )
        del_rec.write({"delegation_state": "revoked"})
        del_rec.unlink()
        rep = env_m["assembly.representation"].create(
            {
                "assembly_id": asm.id,
                "owner_partner_id": partners[0].id,
                "agent_partner_id": partners[1].id,
            }
        )
        rep.unlink()
        env_m["assembly.assembly"].browse(asm.id).unlink()
=======
>>>>>>> origin/18.0
