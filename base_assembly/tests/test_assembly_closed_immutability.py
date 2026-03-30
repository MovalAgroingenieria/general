# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

<<<<<<< HEAD
"""Closed assembly immutability (AF): no related mutations except assembly → cancelled."""
=======
"""AF: assembly in ``closed`` is read-only except transition to ``cancelled``."""
>>>>>>> origin/18.0

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
<<<<<<< HEAD

    def test_closed_blocks_new_attendee(self):
        partner = self._create_partners(self.env, 1, prefix="ClosedAtt")[0]
        assembly, _agenda = self._create_assembly_with_agenda(
            partner_domain="[('id', 'in', %s)]" % partner.ids,
        )
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        assembly.agenda_ids.action_skip()
        assembly.action_close()
        with self.assertRaises(UserError):
            self.env["assembly.attendee"].create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": partner.id,
                }
            )

    def test_closed_blocks_new_voting(self):
        assembly, agenda = self._close_assembly_after_skip_agenda()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        with self.assertRaises(UserError):
            self.env["assembly.voting"].create(
                {
                    "agenda_id": agenda.id,
                    "vote_type_id": vt.id,
                    "name": "Illegal voting",
                }
            )

    def test_closed_blocks_new_delegation(self):
        partners = self._create_partners(self.env, 2, prefix="ClosedDel")
        assembly, agenda = self._create_assembly_with_agenda(
            partner_domain="[('id', 'in', %s)]" % partners.ids,
        )
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        self._confirm_attendees(assembly.attendee_ids, vote_type=vt)
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_skip()
        assembly.action_close()
        p_del, p_def = partners[0], partners[1]
        with self.assertRaises(UserError):
            self.env["assembly.delegation"].create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": p_del.id,
                    "delegate_partner_id": p_def.id,
                    "vote_type_ids": [(6, 0, vt.ids)],
                    "delegation_state": "draft",
                }
            )

    def test_closed_blocks_recompute_votes_on_attendees(self):
        """Stored vote snapshots must not rebuild while the assembly is closed."""
        partner = self._create_partners(self.env, 1, prefix="CloseReco")[0]
        assembly, agenda = self._create_assembly_with_agenda(
            partner_domain="[('id', 'in', %s)]" % partner.ids,
        )
        assembly.action_generate_attendees()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_skip()
        assembly.action_close()
        Attendee = self.env["assembly.attendee"]
        self.assertTrue(assembly.attendee_ids)
        with self.assertRaises(UserError):
            Attendee.recompute_votes(assembly.attendee_ids)
=======
>>>>>>> origin/18.0
