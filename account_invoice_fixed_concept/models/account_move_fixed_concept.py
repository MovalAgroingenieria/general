# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class AccountInvoiceFixedconcept(models.Model):
    _name = "account.move.fixedconcept"
    _description = "Fixed Concept"

    name = fields.Char(
        string="Concept",
        required=True,
        translate=True,
    )

    extra_field = fields.Boolean(
        sgtring="Extra Field",
        help="If checked a free text field will be shown in the invoice.",
    )

    default = fields.Boolean(
        string="Default",
        help="If checked the concept will be used by default.",
    )

    @api.constrains('default')
    def _check_single_default(self):
        for record in self:
            if record.default:
                existing_default = self.search([
                    ('default', '=', True),
                    ('id', '!=', record.id)
                ])
                if existing_default:
                    raise ValidationError(_(
                        "Only one fixed concept can be set as the default."
                    ))
