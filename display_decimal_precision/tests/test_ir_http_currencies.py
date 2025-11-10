# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestIrHttpCurrencies(TransactionCase):
    """Tests for IrHttp.get_currencies override adjusting display digits."""

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.IrHttp = cls.env["ir.http"]
        cls.Currency = cls.env["res.currency"]

    def _make_currency(self, name="TST", symbol="T", decimal_places=2, rounding=0.01):
        """Create a minimal currency."""
        return self.Currency.create(
            {
                "name": name,
                "symbol": symbol,
                "decimal_places": decimal_places,
                "rounding": rounding,
                "active": True,
            }
        )

    def test_fallbacks_to_decimal_places_when_no_display_places(self):
        """When there is no display_decimal_places, use decimal_places."""
        cur = self._make_currency(
            name="TST_DECPL", symbol="D", decimal_places=4, rounding=0.0001
        )

        res = self.IrHttp.get_currencies()
        self.assertIn(cur.id, res, "Currency must be present in ir.http payload")

        digits = res[cur.id].get("digits")
        # Must be a JSON-serializable pair and the scale equals decimal_places
        self.assertIsInstance(digits, list)
        self.assertEqual(len(digits), 2)
        self.assertEqual(digits[1], 4)

    def test_prefers_display_decimal_places_when_present(self):
        """If display_decimal_places exists, prefer it over decimal_places."""
        # Skip if the field isn't available in this DB (module not installed)
        if not hasattr(self.Currency, "display_rounding") or not hasattr(
            self.Currency, "display_decimal_places"
        ):
            self.skipTest("display_decimal_places not available in this environment")

        # Base currency with 2 decimals but visual rounding 0.005 -> 3
        cur = self._make_currency(
            name="TST_VIS", symbol="V", decimal_places=2, rounding=0.01
        )
        cur.write({"display_rounding": 0.005})
        # Ensure the computed field is up to date
        if hasattr(cur, "_compute_display_decimal_places"):
            # pylint: disable=protected-access
            cur._compute_display_decimal_places()
        cur.invalidate_recordset()

        res = self.IrHttp.get_currencies()
        self.assertIn(cur.id, res)

        digits = res[cur.id].get("digits")
        self.assertIsInstance(digits, list)
        self.assertEqual(len(digits), 2)
        # display_decimal_places should be 3 given 0.005
        self.assertEqual(digits[1], int(cur.display_decimal_places or 3))

    def test_digits_are_left_as_list_pair(self):
        """The override must leave 'digits' as a 2-length list (JSON-safe)."""
        cur = self._make_currency(
            name="TST_JSON", symbol="J", decimal_places=3, rounding=0.001
        )
        res = self.IrHttp.get_currencies()
        self.assertIn(cur.id, res)

        digits = res[cur.id].get("digits")
        self.assertIsInstance(digits, list)
        self.assertEqual(len(digits), 2)
        # scale equals decimal_places (3) if no display_decimal_places is defined
        self.assertEqual(digits[1], 3)
