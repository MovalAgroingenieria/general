# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    def _valid_field_parameter(self, field, name):
        if name == "states":
            return True
        return super()._valid_field_parameter(field, name)

    state = fields.Selection(
        selection_add=[("report_label", "Print self-adhesive labels")],
        ondelete={"report_label": "cascade"},
    )
    label_template_view_id = fields.Many2one(
        string="Label QWeb Template",
        comodel_name="ir.ui.view",
        domain=[("type", "=", "qweb")],
        help="The QWeb template key to render the labels",
        states={"report_label": [("required", True)]},
    )
    label_paperformat_id = fields.Many2one(
        "report.paperformat.label",
        "Label Paper Format",
        states={"report_label": [("required", True)]},
    )

    def _run_action_report_label_multi(self, _eval_context=None):
        """Show report label wizard"""
        context = dict(self.env.context)
        context.update(
            {
                "label_template_view_id": self.label_template_view_id.id,
                "label_paperformat_id": self.label_paperformat_id.id,
                "res_model_id": self.model_id.id,
            }
        )
        return {
            "name": self.name,
            "type": "ir.actions.act_window",
            "res_model": "report.label.wizard",
            "context": context,
            "view_mode": "form",
            "target": "new",
        }
