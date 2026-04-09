# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import TransactionCase

from .common import AssemblyTestMixin


class TestAssemblyAttendeeCallRegisterUi(AssemblyTestMixin, TransactionCase):
    def test_call_register_action_loads(self):
        act = self.env.ref("base_assembly.assembly_attendee_action_call_register")
        self.assertEqual(act.res_model, "assembly.attendee")
        self.assertEqual(act.view_mode, "list,form")
        self.assertIn(
            self.env.ref("base_assembly.assembly_group_manager"),
            act.groups_id,
        )
        self.assertEqual(
            act.search_view_id,
            self.env.ref("base_assembly.assembly_attendee_view_search_call_register"),
        )

    def test_call_register_list_arch_has_key_fields(self):
        arch = self.env.ref(
            "base_assembly.assembly_attendee_view_tree_call_register"
        ).arch_db
        for needle in (
            'name="assembly_id"',
            'name="partner_id"',
            'name="participant_partner_id"',
            'name="call_register_representation_agent"',
            'name="partner_vat"',
            'name="attendee_state"',
            'name="date_register"',
            'name="total_votes"',
            'name="call_register_link_ready"',
            'name="attendance_url"',
        ):
            self.assertIn(needle, arch)
