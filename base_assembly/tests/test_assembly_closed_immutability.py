# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""AF: assembly in ``closed`` is read-only except transition to ``cancelled``."""

from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyClosedImmutability(AssemblyTestMixin, TransactionCase):
    def _close_assembly_after_skip_agenda(self):
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_skip()
        assembly.action_close()
        return assembly, agenda

    def test_closed_rejects_write_on_assembly_fields(self):
        assembly, _agenda = self._close_assembly_after_skip_agenda()
        with self.assertRaises(UserError):
            assembly.write({"name": "Tampered"})

    def test_closed_rejects_mixed_state_and_body_write(self):
        assembly, _agenda = self._close_assembly_after_skip_agenda()
        with self.assertRaises(UserError):
            assembly.write(
                {"assembly_state": "cancelled", "name": "Tampered"},
            )

    def test_closed_still_allows_cancel_then_reopen(self):
        assembly, agenda = self._close_assembly_after_skip_agenda()
        assembly.action_cancel()
        self.assertEqual(assembly.assembly_state, "cancelled")
        assembly.action_reopen()
        self.assertEqual(assembly.assembly_state, "draft")

    def test_closed_blocks_agenda_write(self):
        assembly, agenda = self._close_assembly_after_skip_agenda()
        with self.assertRaises(UserError):
            agenda.write({"name": "Changed title"})

    def test_closed_blocks_new_agenda_line(self):
        assembly, _agenda = self._close_assembly_after_skip_agenda()
        with self.assertRaises(UserError):
            self.env["assembly.agenda"].create(
                {
                    "assembly_id": assembly.id,
                    "name": "Extra point",
                    "requires_vote": False,
                }
            )
