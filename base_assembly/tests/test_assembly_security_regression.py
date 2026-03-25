# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Minimal security regression: ACL on ``assembly.assembly``, ``assembly.attendee``, ``assembly.delegation``.

Complements :mod:`test_assembly_security_acl` with a short matrix (create/write/unlink smoke).
"""

import unittest

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblySecurityRegression(AssemblyTestMixin, TransactionCase):
    """``assembly_group_user`` = read-only on critical models; manager retains CRUD."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref("base_assembly.assembly_group_user")
        cls.group_manager = cls.env.ref("base_assembly.assembly_group_manager")
        cls.base_user = cls.env.ref("base.group_user")
        try:
            cls.user_assembly_user = cls.env["res.users"].create(
                {
                    "name": "Assembly User Reg",
                    "login": "assembly_user_reg",
                    "password": "assembly_user_reg",
                    "groups_id": [(6, 0, [cls.base_user.id, cls.group_user.id])],
                }
            )
            cls.user_assembly_manager = cls.env["res.users"].create(
                {
                    "name": "Assembly Manager Reg",
                    "login": "assembly_manager_reg",
                    "password": "assembly_manager_reg",
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
        env_m["assembly.assembly"].browse(asm.id).unlink()
