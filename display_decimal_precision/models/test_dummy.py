# 2023-2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class DisplayDecimalDummy(models.Model):
    _name = "display.decimal.dummy"
    _description = "Dummy model for display decimal precision tests"

    value_2 = fields.Float(digits="Test Precision 2")
    value_3 = fields.Float(digits="Test Precision 3")
