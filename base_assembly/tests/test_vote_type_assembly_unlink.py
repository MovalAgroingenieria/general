# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestVoteTypeAssemblyUnlink(AssemblyTestMixin, TransactionCase):
    def test_unused_vote_type_can_be_deleted(self):
        vt = self._create_vote_type(self.env, name="Unused VT", code="UNUSED_VT_UNLINK")
        vid = vt.id
        vt.unlink()
        self.assertFalse(self.env["vote.type"].browse(vid).exists())

    def test_cannot_delete_vote_type_linked_to_assembly_vote_type_ids(self):
        env = self.env
        vt_used = self._create_vote_type(env, name="On Assembly M2M", code="ASM_M2M_VT")
        vt_other = self._create_vote_type(env, name="Other VT", code="OTHER_VT_ASM")
        atype = self._create_assembly_type(env, name="Type two VT", vote_type=vt_other)
        assembly = self._create_assembly("Asm m2m", assembly_type=atype)
        assembly.write({"vote_type_ids": [(6, 0, (vt_used | vt_other).ids)]})
        with self.assertRaises(UserError) as ctx:
            vt_used.unlink()
        self.assertIn("assemblies", str(ctx.exception).lower())

    def test_cannot_delete_vote_type_linked_to_agenda_vote_type_id(self):
        assembly, agenda = self._create_assembly_with_agenda(name="Asm agenda vt")
        vt = agenda.vote_type_id
        self.assertTrue(vt)
        with self.assertRaises(UserError):
            vt.unlink()

    def test_batch_unlink_blocked_if_any_vote_type_is_used(self):
        env = self.env
        vt_free = self._create_vote_type(env, name="Free VT", code="FREE_VT_BATCH")
        vt_used = self._create_vote_type(env, name="Used VT", code="USED_VT_BATCH")
        atype = self._create_assembly_type(env, vote_type=vt_used)
        self._create_assembly("Batch asm", assembly_type=atype)
        with self.assertRaises(UserError):
            (vt_free | vt_used).unlink()
        self.assertTrue(vt_free.exists())
        self.assertTrue(vt_used.exists())
