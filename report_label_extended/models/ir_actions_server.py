# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    def report_label_associated_view(self):
        """View the associated qweb templates"""
        self.ensure_one()
        res = self.env["ir.actions.act_window"]._for_xml_id(
            "base.action_ui_view"
        )
        if not res or len(self.label_template.split(".")) < 2:
            return False
        res["domain"] = [
            ("type", "=", "qweb"),
            "|",
            ("name", "ilike", self.label_template.split(".")[1]),
            ("key", "=", self.label_template),
        ]
        return res
