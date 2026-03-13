# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models
from odoo.exceptions import ValidationError


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

    def _validate_no_conflict(self, partners):
        """Check that the action does not conflict with existing types."""
        if self.action_type == "mark_primary":
            conflicting = partners.filtered("is_secondary_entity")
            if conflicting:
                names = ", ".join(conflicting.mapped("name"))
                raise ValidationError(
                    self.env._(
                        "The following contacts are already secondary "
                        "members and cannot be marked as primary "
                        "entities: %(names)s",
                        names=names,
                    )
                )
        elif self.action_type == "mark_secondary":
            conflicting = partners.filtered("is_primary_entity")
            if conflicting:
                names = ", ".join(conflicting.mapped("name"))
                raise ValidationError(
                    self.env._(
                        "The following contacts are already primary "
                        "entities and cannot be marked as secondary "
                        "members: %(names)s",
                        names=names,
                    )
                )

    def action_apply(self):
        """Apply the selected action to the selected partners."""
        self.ensure_one()
        active_ids = self.env.context.get("active_ids", [])
        partners = self.env["res.partner"].browse(active_ids)

        self._validate_no_conflict(partners)

        if self.action_type == "mark_primary":
            partners.write({"is_primary_entity": True})
        elif self.action_type == "unmark_primary":
            partners.write({"is_primary_entity": False})
        elif self.action_type == "mark_secondary":
            partners.write({"is_secondary_entity": True})
        elif self.action_type == "unmark_secondary":
            partners.write({"is_secondary_entity": False})

        return {"type": "ir.actions.act_window_close"}
