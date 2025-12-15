# 2023-2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "display_decimal_precision")
class TestIntegration(TransactionCase):

    def test_float_rounding_behavior(self):
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("display_decimal_precision.dp.Test Precision 2", "2")

        model = self.env["display.decimal.dummy"]

        field = model._fields["value_2"]
        desc = field.get_description(self.env)
        self.assertEqual(desc["digits"], (16, 2))
