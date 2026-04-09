# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblySessionVotingUx(TransactionCase, AssemblyTestMixin):
    def test_open_live_weighted_starts_voting_and_roll_metrics(self):
        assembly, agenda = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.vote_type_ids[:1]
        self.assertTrue(vt)
        attendees = assembly.attendee_ids
        self._confirm_attendees(attendees, vote_type=vt, votes_each=1)
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        action = agenda.action_open_live_voting_screen()
        self.assertEqual(action.get("res_model"), "assembly.voting")
        voting = self.env["assembly.voting"].browse(action["res_id"])
        self.assertEqual(voting.voting_state, "open")
        self.assertEqual(voting.agenda_id, agenda)
        line = voting.vote_line_ids[:1]
        self.assertTrue(line)
        self.assertEqual(line.session_row_status_label, line.env._("Pending"))
        line.action_session_vote_yes()
        self.assertEqual(line.vote_option, "yes")
        self.assertEqual(line.session_row_status_label, line.env._("Recorded"))
        self.assertGreaterEqual(voting.count_recorded_votes, 1)
        self.assertGreaterEqual(voting.total_votes_cast, 0.0)
        line.action_session_vote_clear()
        self.assertEqual(line.vote_option, "unset")

    def test_session_row_ui_ineligible_when_zero_weight(self):
        line = self.env["assembly.voting.line"].new(
            {"votes_applied": 0.0, "vote_option": "unset"}
        )
        line._compute_session_row_ui()
        self.assertEqual(line.session_control_state, "ineligible")
        self.assertEqual(line.session_row_status_label, line.env._("Not eligible"))

    def test_session_navigate_skips_no_vote_item(self):
        assembly, agenda1 = self._create_assembly_with_agenda(
            agenda_title="W1",
        )
        seq = self._next_agenda_sequence(assembly)
        self.env["assembly.agenda"].create(
            {
                "assembly_id": assembly.id,
                "sequence": seq,
                "name": "Info only",
                "agenda_vote_mode": "no_vote",
                "requires_vote": False,
            }
        )
        partners = self._create_partners(self.env, 2)
        assembly.partner_domain = "[('id', 'in', %s)]" % partners.ids
        assembly.action_generate_attendees()
        vt = assembly.vote_type_ids[:1]
        self._confirm_attendees(assembly.attendee_ids, vote_type=vt, votes_each=1)
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda1.action_open_live_voting_screen()
        out = agenda1.action_session_navigate_live_voting(1)
        self.assertEqual(out.get("type"), "ir.actions.client")

    def test_manual_session_totals_and_variance_flag(self):
        assembly, agenda = self._create_assembly_with_agenda(
            requires_vote=False,
        )
        p_one, p_two = self._create_partners(self.env, 2)
        assembly.partner_domain = "[('id', 'in', (%s, %s))]" % (p_one.id, p_two.id)
        assembly.action_generate_attendees()
        vt = assembly.vote_type_ids[:1]
        self._confirm_attendees(assembly.attendee_ids, vote_type=vt, votes_each=1)
        agenda.write(
            {
                "agenda_vote_mode": "manual_yes_no",
                "manual_yes": 2,
                "manual_no": 0,
                "manual_abstain": 0,
                "manual_count_blank": 0,
            }
        )
        self.assertFalse(agenda.session_manual_has_variance)
        draft_like = self.env["assembly.agenda"].new(
            {
                "assembly_id": assembly.id,
                "agenda_vote_mode": "manual_yes_no",
                "manual_yes": 2,
                "manual_no": 1,
                "manual_abstain": 0,
                "manual_count_blank": 0,
            }
        )
        draft_like._compute_session_manual_totals()
        self.assertTrue(draft_like.session_manual_has_variance)

    def test_live_dashboard_prefers_open_voting(self):
        assembly, agenda = self._create_assembly_with_agenda()
        partners = self._create_partners(self.env, 2)
        assembly.partner_domain = "[('id', 'in', %s)]" % partners.ids
        assembly.action_generate_attendees()
        vt = assembly.vote_type_ids[:1]
        self._confirm_attendees(assembly.attendee_ids, vote_type=vt, votes_each=1)
        assembly.action_announce()
        assembly.action_open_registration()
        assembly.action_start_session()
        agenda.action_start_voting()
        voting = self.env["assembly.voting"].search(
            [("agenda_id", "=", agenda.id)], limit=1
        )
        action = assembly.action_open_live_voting_dashboard()
        self.assertEqual(action.get("res_id"), voting.id)

    def test_live_dashboard_requires_in_session(self):
        assembly, _agenda = self._create_assembly_with_agenda()
        with self.assertRaises(UserError):
            assembly.action_open_live_voting_dashboard()
