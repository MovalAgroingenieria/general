# 2023-2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "display_decimal_precision")
class TestResConfigSettings(TransactionCase):

    def test_settings_store_parameters(self):
        settings = self.env["res.config.settings"].create({
            "dp_product_price": 5,
            "dp_product_uom": 2,
        })
        settings.set_values()

        icp = self.env["ir.config_parameter"].sudo()
        self.assertEqual(
            icp.get_param("display_decimal_precision.dp.Product Price"),
            "5",
        )
        self.assertEqual(
            icp.get_param("display_decimal_precision.dp.Product Unit of Measure"),
            "2",
        )
