# 2023-2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "display_decimal_precision")
class TestDecimalPrecision(TransactionCase):

    def test_display_precision_from_decimal_precision(self):
        dp = self.env["decimal.precision"].create({
            "name": "Test Precision",
            "digits": 6,
            "display_digits": 3,
        })

        precision = self.env["decimal.precision"].get_display_precision(
            "Test Precision"
        )
        self.assertEqual(precision, (16, 3))

    def test_display_precision_from_config_parameter(self):
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("display_decimal_precision.dp.Test Precision", "4")

        precision = self.env["decimal.precision"].get_display_precision("Test Precision")
        self.assertEqual(precision, (16, 4))
