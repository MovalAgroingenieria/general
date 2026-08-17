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


class AssemblyOpenAssemblyMixin(models.AbstractModel):
    _name = "assembly.mixin.open.assembly"
    _description = "Mixin: open the related assembly form"

    def action_open_assembly(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Assembly"),
            "res_model": "assembly.assembly",
            "res_id": self.assembly_id.id,
            "view_mode": "form",
            "target": "current",
        }
