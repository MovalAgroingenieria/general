# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class AssemblyWindowActionMixin(models.AbstractModel):
    _name = "assembly.mixin.window_action"
    _description = "Mixin: standard window actions"

    def _action_window(
        self,
        res_model,
        name,
        view_mode,
        *,
        res_id=None,
        domain=None,
        context=None,
    ):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": res_model,
            "view_mode": view_mode,
            "target": "current",
        }
        if res_id is not None:
            action["res_id"] = res_id
        if domain is not None:
            action["domain"] = domain
        if context is not None:
            action["context"] = context
        return action


class AssemblyOpenAssemblyMixin(models.AbstractModel):
    _name = "assembly.mixin.open.assembly"
    _inherit = ["assembly.mixin.window_action"]
    _description = "Mixin: open assembly form (assembly_id)"

    def action_open_assembly(self):
        return self._action_window(
            "assembly.assembly",
            self.env._("Assembly"),
            "form",
            res_id=self.assembly_id.id,
        )
