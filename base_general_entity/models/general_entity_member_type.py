# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class GeneralEntityMemberType(models.Model):
    _name = "general.entity.member.type"
    _description = "Entity Member Type"
    _order = "sequence, code, name"

    code = fields.Char(
        required=True,
        index=True,
    )
    name = fields.Char(
        required=True,
    )
    sequence = fields.Integer(
        default=10,
    )
    active = fields.Boolean(
        default=True,
    )
    note = fields.Text()

    _sql_constraints = [
        (
            "unique_code",
            "unique(code)",
            "The member type code must be unique.",
        ),
    ]
