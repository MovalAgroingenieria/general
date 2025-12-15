# 2023-2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests.common import TransactionCase, tagged
from odoo import fields, models


class DummyModel(models.Model):
    _name = "display.decimal.dummy"
    _description = "Dummy model for decimal precision tests"

    value = fields.Float(digits="Product Price")


@tagged("post_install", "-at_install", "display_decimal_precision")
class TestFieldDescription(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.setup_models(cls.env.cr)

    def test_field_description_uses_display_precision(self):
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("display_decimal_precision.dp.Test Precision 3", "3")

        field = self.env["display.decimal.dummy"]._fields["value_3"]
        desc = field.get_description(self.env)

        self.assertIn("digits", desc)
        self.assertEqual(desc["digits"], (16, 3))
