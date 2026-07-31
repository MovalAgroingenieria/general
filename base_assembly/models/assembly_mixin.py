# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


def assembly_safe_report_filename(label, default="record"):
    if label in (None, False):
        text = ""
    else:
        text = str(label).strip()
    if not text:
        return default
    for char in ("/", "\\", ":", "*", "?", '"', "<", ">", "|", "\n", "\r"):
        text = text.replace(char, "-")
    text = " ".join(text.split())
    return text[:120] if text else default


# oca-review: shared helper + abstract mixins are intentionally co-located.
class AssemblyWindowActionMixin(models.AbstractModel):
    _name = "assembly.mixin.window_action"
    _description = "Mixin: standard window actions"

    def _action_window(self, res_model, name, view_mode, *, extra=None):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": res_model,
            "view_mode": view_mode,
            "target": "current",
        }
        if extra:
            action.update(extra)
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
            extra={"res_id": self.assembly_id.id},
        )
