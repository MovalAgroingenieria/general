# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=protected-access

import uuid

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestResCurrencyDisplayRounding(TransactionCase):
    """Tests for display_rounding and computed display_decimal_places
    on res.currency."""

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.Currency = cls.env["res.currency"]

    # -------------------------
    # Helpers
    # -------------------------
    def _new_currency(self, *, name=None, symbol="T", decimal_places=2):
        """Create a minimal currency with consistent rounding = 10^-decimal_places."""
        name = name or f"TST-{uuid.uuid4()}"
        rounding = 10 ** (-int(decimal_places or 0))
        return self.Currency.create(
            {
                "name": name,
                "symbol": symbol,
                "decimal_places": decimal_places,
                "rounding": rounding,
                "active": True,
            }
        )

    # -------------------------
    # Core compute behavior
    # -------------------------
    def test_fallback_to_decimal_places_when_display_rounding_falsy(self):
        """If display_rounding is falsy, use native decimal_places."""
        cur = self._new_currency(decimal_places=4)
        # Ensure falsy: either not set or zero
        cur.write({"display_rounding": 0})
        cur.invalidate_recordset()
        if hasattr(cur, "_compute_display_decimal_places"):
            cur._compute_display_decimal_places()
        self.assertEqual(cur.display_decimal_places, 4)

    def test_display_rounding_to_decimals_typical_values(self):
        """0.01 -> 2; 0.005 -> 3; >= 1 -> 0."""
        cur = self._new_currency(decimal_places=2)

        # 0.01 -> 2
        cur.write({"display_rounding": 0.01})
        cur.invalidate_recordset()
        cur._compute_display_decimal_places()
        self.assertEqual(cur.display_decimal_places, 2)

        # 0.005 -> 3
        cur.write({"display_rounding": 0.005})
        cur.invalidate_recordset()
        cur._compute_display_decimal_places()
        self.assertEqual(cur.display_decimal_places, 3)

        # 1 -> 0 (and anything >= 1)
        cur.write({"display_rounding": 1})
        cur.invalidate_recordset()
        cur._compute_display_decimal_places()
        self.assertEqual(cur.display_decimal_places, 0)

        cur.write({"display_rounding": 2})
        cur.invalidate_recordset()
        cur._compute_display_decimal_places()
        self.assertEqual(cur.display_decimal_places, 0)

    def test_guard_against_floating_noise(self):
        """Noise like 0.1000000000003 should behave like ~0.1 → 1 decimal."""
        cur = self._new_currency(decimal_places=2)
        cur.write({"display_rounding": 0.1000000000003})
        cur.invalidate_recordset()
        cur._compute_display_decimal_places()
        self.assertEqual(cur.display_decimal_places, 1)

    def test_clamp_upper_bound_6_with_storage_precision_boundary(self):
        """With digits=(12,6), the smallest storable positive is 1e-6 -> 6 decimals.

        Values smaller than 1e-6 round to 0 at assignment, so we can't reach 12 here.
        """
        cur = self._new_currency(decimal_places=2)
        cur.write({"display_rounding": 10**-6})  # 1e-6 is representable with 6 decimals
        cur.invalidate_recordset()
        cur._compute_display_decimal_places()
        self.assertEqual(cur.display_decimal_places, 6)

    # -------------------------
    # Constraints and onchange
    # -------------------------
    def test_constraint_negative_raises(self):
        """Negative display_rounding should raise ValidationError."""
        cur = self._new_currency()
        with self.assertRaises(ValidationError):
            cur.write({"display_rounding": -0.01})

    def test_onchange_warning_negative(self):
        """Onchange warning is returned on negative values without writing."""
        # Use a transient new() record to avoid write() and constraints firing
        rec = self.Currency.new({})
        rec.display_rounding = -0.1
        res = rec._onchange_display_rounding()
        self.assertIsInstance(res, dict)
        self.assertIn("warning", res)
        self.assertIn("title", res["warning"])
        self.assertIn("message", res["warning"])

        # Neutral when valid
        rec.display_rounding = 0.01
        res_ok = rec._onchange_display_rounding()
        self.assertEqual(res_ok, {})

    def test_too_small_positive_skipped_due_to_storage_precision(self):
        """Document behavior: with digits=(12,6), values < 1e-12 round to 0 on assign.

        Therefore the constraint branch '0 < dr < 1e-12' cannot be hit via write();
        attempting to set such a small value results in 0, which is treated as falsy.
        """
        self.skipTest(
            "Not testable with field digits=(12,6); value "
            "rounds to 0 before constraint."
        )
