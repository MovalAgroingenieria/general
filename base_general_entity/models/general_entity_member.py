# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GeneralEntityMember(models.Model):
    _name = "general.entity.member"
    _description = "General Entity Member"
    _order = "sequence, primary_partner_id, member_partner_id, member_code_in_entity"

    primary_partner_id = fields.Many2one(
        comodel_name="res.partner",
        required=True,
        index=True,
        ondelete="cascade",
        domain=[("is_primary_entity", "=", True)],
    )
    member_partner_id = fields.Many2one(
        comodel_name="res.partner",
        required=True,
        index=True,
        ondelete="cascade",
        domain=[("is_secondary_entity", "=", True)],
    )
    member_code_in_entity = fields.Char(
        index=True,
        help="Member code within this specific entity",
    )
    entity_global_code = fields.Char(
        related="member_partner_id.entity_global_code",
        readonly=True,
        store=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        index=True,
        # pylint: disable=protected-access
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(
        default=True,
        help="Uncheck to deactivate this relationship without deleting it",
    )
    sequence = fields.Integer(
        default=10,
        help="Display order",
    )
    note = fields.Text()

    _sql_constraints = [
        (
            "unique_primary_member_company",
            "unique(primary_partner_id, member_partner_id, company_id)",
            "This member is already related to this primary entity in this company.",
        ),
    ]

    @api.constrains("primary_partner_id", "member_code_in_entity")
    def _check_unique_member_code(self):
        """Validate that the local code is unique within the entity."""
        for record in self:
            if record.member_code_in_entity:
                domain = [
                    ("primary_partner_id", "=", record.primary_partner_id.id),
                    ("member_code_in_entity", "=", record.member_code_in_entity),
                    ("id", "!=", record.id),
                ]
                if self.search_count(domain):
                    raise ValidationError(
                        self.env._(
                            "Another member with code %(code)s already "
                            "exists in this entity",
                            code=record.member_code_in_entity,
                        )
                    )

    @api.depends(
        "primary_partner_id.name", "member_partner_id.name", "member_code_in_entity"
    )
    def _compute_display_name(self):
        for record in self:
            name = "{} - {}".format(
                record.primary_partner_id.name or "",
                record.member_partner_id.name or "",
            )
            if record.member_code_in_entity:
                name = "[{}] {}".format(record.member_code_in_entity, name)
            record.display_name = name
