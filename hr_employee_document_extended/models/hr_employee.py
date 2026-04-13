# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    def action_get_attachment_tree_view(self):
        action = super().action_get_attachment_tree_view()
        kanban_view = self.env.ref(
            "hr_employee_document_extended"
            ".view_ir_attachment_kanban_employee_document"
        )
        action["views"] = [(kanban_view.id, "kanban")] + [
            (view_id, view_type)
            for view_id, view_type in action.get("views", [])
            if view_type != "kanban"
        ]
        return action
