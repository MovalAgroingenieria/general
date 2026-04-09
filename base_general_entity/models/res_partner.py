# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_primary_entity = fields.Boolean(
        index=True,
        help="Check if this contact is a primary entity",
    )
    is_secondary_entity = fields.Boolean(
        index=True,
        help="Check if this contact is a secondary member",
    )
    entity_global_code = fields.Integer(
        index=True,
        copy=False,
        help="Global shared code (applies to primary and secondary entities)",
    )
    member_type_id = fields.Many2one(
        comodel_name="general.entity.member.type",
        index=True,
        help="Classification type for secondary members",
    )
    member_ids = fields.One2many(
        comodel_name="general.entity.member",
        inverse_name="primary_partner_id",
    )
    member_count = fields.Integer(
        compute="_compute_member_count",
    )
    primary_entity_ids = fields.One2many(
        comodel_name="general.entity.member",
        inverse_name="member_partner_id",
    )

    @api.depends("member_ids")
    def _compute_member_count(self):
        for partner in self:
            partner.member_count = len(partner.member_ids)

    @api.constrains("is_primary_entity", "is_secondary_entity")
    def _check_entity_types(self):
        """Optional: validate that a contact cannot be both."""
        for partner in self:
            if partner.is_primary_entity and partner.is_secondary_entity:
                raise ValidationError(
                    self.env._(
                        "A contact cannot be both a primary entity and "
                        "a secondary member simultaneously."
                    )
                )

    @api.constrains("entity_global_code", "is_primary_entity")
    def _check_unique_code_primary(self):
        """Code must be unique among primary entities."""
        for partner in self:
            if not partner.entity_global_code or not partner.is_primary_entity:
                continue
            duplicate = self.search(
                [
                    ("entity_global_code", "=", partner.entity_global_code),
                    ("is_primary_entity", "=", True),
                    ("id", "!=", partner.id),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    self.env._(
                        "A primary entity with code %(code)s already "
                        "exists: %(name)s",
                        code=partner.entity_global_code,
                        name=duplicate.name,
                    )
                )

    @api.constrains("entity_global_code", "member_type_id", "is_secondary_entity")
    def _check_unique_code_per_type(self):
        """Code must be unique per member_type (for secondary members)."""
        for partner in self:
            if not partner.entity_global_code or not partner.is_secondary_entity:
                continue
            domain = [
                ("entity_global_code", "=", partner.entity_global_code),
                ("member_type_id", "=", partner.member_type_id.id),
                ("is_secondary_entity", "=", True),
                ("id", "!=", partner.id),
            ]
            duplicate = self.search(domain, limit=1)
            if duplicate:
                raise ValidationError(
                    self.env._(
                        "A member with code %(code)s and type '%(type)s' "
                        "already exists: %(name)s",
                        code=partner.entity_global_code,
                        type=partner.member_type_id.name or "-",
                        name=duplicate.name,
                    )
                )

    def action_view_members(self):
        """Open members view of the primary entity."""
        self.ensure_one()
        action = self.env.ref(
            "base_general_entity.action_general_entity_member"
        ).read()[0]
        action["domain"] = [("primary_partner_id", "=", self.id)]
        action["context"] = {
            "default_primary_partner_id": self.id,
        }
        return action
