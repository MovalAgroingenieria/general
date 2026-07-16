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

    def _next_entity_global_code(self, is_primary):
        """Return the next global code for the given entity kind.

        Primary entities and secondary members keep independent
        consecutive sequences (highest value of their own kind + 1).
        """
        if is_primary:
            query = (
                "SELECT COALESCE(MAX(entity_global_code), 0) "
                "FROM res_partner WHERE is_primary_entity = TRUE"
            )
        else:
            query = (
                "SELECT COALESCE(MAX(entity_global_code), 0) "
                "FROM res_partner WHERE is_secondary_entity = TRUE"
            )
        self.env.cr.execute(query)
        return (self.env.cr.fetchone()[0] or 0) + 1

    @api.model
    def default_get(self, fields_list):
        """Preview the next global code in the form for new entities.

        Only when creating a primary entity or a secondary member (detected
        from the action context) and no code was provided yet. Each kind
        uses its own consecutive sequence.
        """
        defaults = super().default_get(fields_list)
        if "entity_global_code" in fields_list and not defaults.get(
            "entity_global_code"
        ):
            context = self.env.context
            is_primary = context.get("default_is_primary_entity")
            is_secondary = context.get("default_is_secondary_entity")
            if is_primary or is_secondary:
                defaults["entity_global_code"] = self._next_entity_global_code(
                    bool(is_primary)
                )
        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-assign a growing global code to new entities.

        Primary entities and secondary members keep separate consecutive
        sequences. Only applied when no code is provided (empty or 0);
        existing/manual codes are always respected.
        """
        records = super().create(vals_list)
        for is_primary in (True, False):
            pending = records.filtered(
                lambda partner, primary=is_primary: (
                    (
                        partner.is_primary_entity
                        if primary
                        else partner.is_secondary_entity
                    )
                    and not partner.entity_global_code
                )
            )
            if not pending:
                continue
            next_code = self._next_entity_global_code(is_primary)
            for partner in pending:
                partner.entity_global_code = next_code
                next_code += 1
        return records

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
