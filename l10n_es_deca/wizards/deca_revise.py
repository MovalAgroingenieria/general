# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class DecaRevise(models.TransientModel):
    _name = "deca.revise"
    _description = "DECA Revision Wizard"

    deca_id = fields.Many2one(
        "deca.document",
        string="DECA",
        required=True,
    )
    reason = fields.Char(required=True)

    def action_confirm(self):
        self.ensure_one()
        self.deca_id.write(
            {
                "state": "draft",
                "pending_revision_reason": self.reason,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "deca.document",
            "res_id": self.deca_id.id,
            "view_mode": "form",
            "target": "current",
        }
