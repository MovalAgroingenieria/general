# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class PartnerEntityTypeWizard(models.TransientModel):
    _name = "partner.entity.type.wizard"
    _description = "Mark/Unmark Partners as Primary/Secondary Entities"

    action_type = fields.Selection(
        [
            ("mark_primary", "Mark as Primary Entity"),
            ("unmark_primary", "Unmark as Primary Entity"),
            ("mark_secondary", "Mark as Secondary Member"),
            ("unmark_secondary", "Unmark as Secondary Member"),
        ],
        required=True,
    )

    def action_apply(self):
        """Apply the selected action to the selected partners."""
        self.ensure_one()
        active_ids = self.env.context.get("active_ids", [])
        partners = self.env["res.partner"].browse(active_ids)

        if self.action_type == "mark_primary":
            partners.write({"is_primary_entity": True})
        elif self.action_type == "unmark_primary":
            partners.write({"is_primary_entity": False})
        elif self.action_type == "mark_secondary":
            partners.write({"is_secondary_entity": True})
        elif self.action_type == "unmark_secondary":
            partners.write({"is_secondary_entity": False})

        return {"type": "ir.actions.act_window_close"}
