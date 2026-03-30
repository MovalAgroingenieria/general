# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""AF v1.5 core behavior must remain after AF v2 (agenda vote modes, etc.).

Regression anchors: default weighted roll-call, delegation math, people-quorum,
and assembly-level vote recompute — not replaced by manual_multi / no_vote paths.
"""

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAfV15CoreCompat(AssemblyTestMixin, TransactionCase):
    def test_v15_default_agenda_is_weighted_roll_call(self):
        """Legacy entrypoint ``_create_assembly_with_agenda`` still opens weighted mode."""
        assembly, agenda = self._create_assembly_with_agenda(
            name="V15 weighted default"
        )
        self.assertEqual(agenda.agenda_vote_mode, "weighted")
        self.assertTrue(agenda.requires_vote)
        self.assertTrue(agenda.vote_type_id)
        self.assertEqual(agenda.vote_type_id, assembly.vote_type_ids[0])

    def test_v15_weighted_roll_call_refresh_materializes_lines(self):
        """Roll-call grid still fills from confirmed attendees with positive vote weight."""
        assembly, agenda = self._create_assembly_with_agenda(name="V15 roll lines")
        vt = assembly.vote_type_ids[0]
        assembly.action_generate_attendees()
        self._confirm_attendees(assembly.attendee_ids, vote_type=vt, votes_each=1)
        voting = self._open_voting_on_agenda(assembly, agenda)
        self.assertEqual(voting.agenda_id.agenda_vote_mode, "weighted")
        voting.action_refresh_roll_call()
        self.assertEqual(len(voting.vote_line_ids), len(assembly.attendee_ids))
        for line in voting.vote_line_ids:
            self.assertEqual(line.vote_option, "unset")

    def test_v15_quorum_counts_registered_delegator_when_delegate_confirmed(self):
        """People-quorum: delegator without confirmation still counts if delegation is effective."""
        assembly, partners = self._assembly_two_partner_setup_for_quorum()
        vt = assembly.vote_type_ids[0]
        delegator = assembly.attendee_ids.filtered(
            lambda a: a.partner_id == partners[0]
        )
        delegate = assembly.attendee_ids.filtered(lambda a: a.partner_id == partners[1])
        self._give_partner_votes(delegator.partner_id, vt, 1)
        self._give_partner_votes(delegate.partner_id, vt, 1)
        delegate.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vt.ids)],
                "delegation_state": "confirmed",
            }
        )
        assembly.invalidate_recordset()
        present = assembly._get_present_partner_ids()
        self.assertEqual(len(present), 2)
        self.assertIn(delegator.partner_id.id, present)
        self.assertIn(delegate.partner_id.id, present)

    def test_v15_delegation_inbound_and_assembly_recompute_votes(self):
        """Delegate snapshot still receives ``delegated_in``; assembly recompute refreshes lines."""
        assembly, partners = self._assembly_two_partner_setup_for_quorum()
        vt = assembly.vote_type_ids[0]
        delegator = assembly.attendee_ids.filtered(
            lambda a: a.partner_id == partners[0]
        )
        delegate = assembly.attendee_ids.filtered(lambda a: a.partner_id == partners[1])
        self._give_partner_votes(delegator.partner_id, vt, 7)
        self._give_partner_votes(delegate.partner_id, vt, 3)
        delegate.action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vt.ids)],
                "delegation_state": "confirmed",
            }
        )
        assembly.action_recompute_attendee_votes()
        line = self.env["assembly.attendee.vote"].search(
            [
                ("attendee_id", "=", delegate.id),
                ("vote_type_id", "=", vt.id),
            ],
            limit=1,
        )
        self.assertTrue(line)
        self.assertEqual(line.delegated_in_votes, 7.0)
        self.assertEqual(line.own_votes, 3.0)

    def test_v15_votes_applied_frozen_after_cast_despite_attendee_recompute(self):
        """Weighted roll-call: cast line keeps ``votes_applied`` after partner totals change (Rule 10)."""
        assembly, agenda = self._create_assembly_with_agenda(name="V15 freeze votes")
        vt = assembly.vote_type_ids[0]
        partners = self._create_partners(self.env, 1, prefix="V15F")
        assembly.write({"partner_domain": "[('id', 'in', %s)]" % partners.ids})
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        self._give_partner_votes(att.partner_id, vt, 5)
        att.action_confirm()
        voting = self._open_voting_on_agenda(assembly, agenda)
        voting.action_refresh_roll_call()
        line = voting.vote_line_ids.filtered(lambda row: row.attendee_id == att)
        self.assertTrue(line)
        snapshot = line.votes_applied
        self.assertEqual(snapshot, 5.0)
        line.write({"vote_option": "yes"})
        self._give_partner_votes(att.partner_id, vt, 50)
        att.recompute_attendee_vote_lines()
        line.invalidate_recordset()
        self.assertEqual(line.votes_applied, snapshot)

    def test_v15_manager_attendance_deep_link_path(self):
        """Attendance entry for managers remains ``GET /assembly/attendance`` (participant = partner id)."""
        partners = self._create_partners(self.env, 1, prefix="V15ATT")
        assembly, _agenda = self._create_assembly_with_agenda(
            name="V15 attendance path",
            partner_domain="[('id', 'in', %s)]" % partners.ids,
        )
        assembly.action_generate_attendees()
        att = assembly.attendee_ids[0]
        url = att._attendance_flow_target_url()
        self.assertIn("/assembly/attendance", url)
        self.assertIn("assembly_id=%s" % assembly.id, url)
        self.assertIn("participant_id=%s" % att.partner_id.id, url)

    def test_v15_voting_ballot_report_keeps_weighted_roll_call_row(self):
        """Original ballot layout: weighted items still show the roll-call checkbox row (not manual-only)."""
        assembly, agenda = self._create_assembly_with_agenda(name="V15 ballot weighted")
        self.assertEqual(agenda.agenda_vote_mode, "weighted")
        report = self.env.ref(
            "base_assembly.assembly_assembly_action_report_voting_ballot"
        )
        html, _ = report._render_qweb_html(report.id, assembly.ids, data={})
        body = html.decode() if isinstance(html, bytes) else html
        self.assertIn("Yes ☐", body)

    def _assembly_two_partner_setup_for_quorum(self):
        """Two convoked partners, one agenda line (weighted), attendees generated."""
        partners = self._create_partners(self.env, 2, prefix="V15Q")
        domain = "[('id', 'in', %s)]" % partners.ids
        assembly, _agenda = self._create_assembly_with_agenda(
            name="V15 quorum del",
            partner_domain=domain,
        )
        assembly.action_generate_attendees()
        return assembly, partners
