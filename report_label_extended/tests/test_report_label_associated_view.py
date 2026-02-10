# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase


class TestReportLabelAssociatedView(TransactionCase):
    """Tests for ir.actions.server.report_label_associated_view (see model in
    report_label_extended.models.ir_actions_server).
    """

    def test_report_label_associated_view_returns_false_without_label_template(self):
        action = self.env["ir.actions.server"].create(
            {"name": "Test", "model_id": self.env.ref("base.model_res_partner").id}
        )
        self.assertFalse(action.report_label_associated_view())
