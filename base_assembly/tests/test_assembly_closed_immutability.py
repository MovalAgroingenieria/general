# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Closed assembly immutability (AF): no related mutations except assembly → cancelled."""

import uuid

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

    def test_closed_blocks_assembly_unlink(self):
        assembly, _agenda = self._close_assembly_after_skip_agenda()
        with self.assertRaises(UserError):
            assembly.unlink()

    def test_closed_blocks_agenda_option_write(self):
        assembly = self._create_assembly()
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Manual multi",
                "agenda_vote_mode": "manual_multi",
                "requires_vote": False,
                "manual_total_expected": 0,
                "option_ids": [
                    (0, 0, {"name": "A", "sequence": 10, "manual_vote_count": 0}),
                ],
            }
        )
        opt = agenda.option_ids[0]
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_skip()
        assembly.action_close()
        with self.assertRaises(UserError):
            opt.write({"manual_vote_count": 1})

    def test_closed_blocks_agenda_option_create(self):
        assembly = self._create_assembly()
        agenda = self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "name": "Manual multi",
                "agenda_vote_mode": "manual_multi",
                "requires_vote": False,
                "manual_total_expected": 0,
                "option_ids": [
                    (0, 0, {"name": "A", "sequence": 10, "manual_vote_count": 0}),
                ],
            }
        )
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_skip()
        assembly.action_close()
        Option = self.env["assembly.agenda.option"]
        with self.assertRaises(UserError):
            Option.create(
                {
                    "agenda_id": agenda.id,
                    "name": "B",
                    "sequence": 20,
                    "manual_vote_count": 0,
                }
            )

    def test_closed_blocks_voting_line_unlink(self):
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vote_type, 2)
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
                "votes_applied": 2.0,
            }
        )
        voting.action_close()
        assembly.action_close()
        with self.assertRaises(UserError):
            line.unlink()

    def test_closed_rejects_direct_state_write_to_in_session(self):
        assembly, _agenda = self._close_assembly_after_skip_agenda()
        with self.assertRaises(UserError):
            assembly.write({"assembly_state": "in_session"})

    def test_action_reopen_from_closed_restores_write(self):
        assembly, _agenda = self._close_assembly_after_skip_agenda()
        assembly.action_reopen_from_closed()
        self.assertEqual(assembly.assembly_state, "in_session")
        assembly.write({"name": "Adjusted after reopen"})
        self.assertEqual(assembly.name, "Adjusted after reopen")

    def test_action_reopen_from_closed_posts_chatter(self):
        assembly, _agenda = self._close_assembly_after_skip_agenda()
        before = len(assembly.message_ids)
        assembly.action_reopen_from_closed()
        self.assertGreater(len(assembly.message_ids), before)
        bodies = assembly.message_ids.mapped("body")
        self.assertTrue(
            any("reopened from closed" in (b or "").lower() for b in bodies)
        )

    def test_action_reopen_from_closed_requires_manager_group(self):
        assembly, _agenda = self._close_assembly_after_skip_agenda()
        login = "asm_nomg_%s" % uuid.uuid4().hex[:8]
        user = self.env["res.users"].create(
            {
                "name": "Assembly user only",
                "login": login,
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("base_assembly.assembly_group_user").id,
                        ],
                    )
                ],
            }
        )
        with self.assertRaises(UserError):
            assembly.with_user(user).action_reopen_from_closed()

    def test_reopen_context_alone_does_not_bypass_without_action(self):
        assembly, _agenda = self._close_assembly_after_skip_agenda()
        with self.assertRaises(UserError):
            assembly.with_context(assembly_reopen_from_closed=True).write(
                {"name": "Hack"}
            )

    def test_closed_blocks_send_to_partners(self):
        assembly, _agenda = self._close_assembly_after_skip_agenda()
        partner = self._create_partners(self.env, 1, prefix="MailCl")[0]
        partner.write({"email": "closed_mail@test.example.com"})
        svc = self.env["assembly.mail.communication"]
        with self.assertRaises(UserError):
            svc.send_to_partners(
                assembly,
                partner,
                primary_kind="publication",
                attachment_options={},
            )

    def test_closed_blocks_ballot_print_wizard(self):
        assembly, _agenda = self._close_assembly_after_skip_agenda()
        wiz = self.env["assembly.ballot.print.wizard"].create(
            {"assembly_id": assembly.id}
        )
        with self.assertRaises(UserError):
            wiz.action_print_ballots()

    def test_closed_blocks_action_recompute_attendee_votes(self):
        partner = self._create_partners(self.env, 1, prefix="RecoAct")[0]
        assembly, _agenda = self._create_assembly_with_agenda(
            partner_domain="[('id', 'in', %s)]" % partner.ids,
        )
        assembly.action_generate_attendees()
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        _agenda.action_skip()
        assembly.action_close()
        self.assertTrue(assembly.attendee_ids)
        with self.assertRaises(UserError):
            assembly.action_recompute_attendee_votes()
