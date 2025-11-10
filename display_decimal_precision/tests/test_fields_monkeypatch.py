# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=protected-access

import uuid
from unittest.mock import patch

from odoo import fields

# Canonical Odoo import path for the addon under test
from odoo.addons.display_decimal_precision.models import fields as dp_fields_mod
from odoo.tests.common import TransactionCase, tagged


def _unique_app(base: str) -> str:
    """Return a unique application name to avoid ormcache hits."""
    return f"{base}::{uuid.uuid4()}"


@tagged("post_install", "-at_install")
class TestFieldGetDescriptionMonkeyPatch(TransactionCase):
    """Tests for the v18-safe Field.get_description monkey-patch."""

    # No cache clearing needed: we use unique application names per test.

    # ------------------------
    # Helper: build a bare Float
    # ------------------------
    def _float_field(self, related_digits=None, digits=None):
        """Create a Float field suitable for get_description()."""
        if related_digits is not None:
            TestFloat = type(
                "TestFloat",
                (fields.Float,),
                {"_related__digits": related_digits},
            )
            f = TestFloat(digits=digits) if digits is not None else TestFloat()
        else:
            f = fields.Float(digits=digits) if digits is not None else fields.Float()

        # Minimal metadata so get_description() doesn't crash
        f.name = "x_test_float"
        f.model_name = "x.test.model"
        f.string = "Test Float"

        # Asegurar que _digits esté configurado
        if digits is not None:
            f._digits = digits

        return f

    # ------------------------
    # Core behavior
    # ------------------------
    def test_injects_digits_from_config_parameter(self):
        """Inject (16, scale) when _related__digits is a string
        and module is installed."""
        app = _unique_app("Product Price")
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param(f"customer_purchase_follow_up.dp.{app}", "3")

        float_field = self._float_field(related_digits=app)

        with patch.object(dp_fields_mod, "_is_ddp_installed", return_value=True):
            desc = float_field.get_description(self.env)
            self.assertEqual(desc.get("type"), "float")
            self.assertEqual(desc.get("digits"), (16, 3))

    def test_respects_existing_digits_on_field(self):
        """Do not overwrite digits if the field already defines them explicitly."""
        app = _unique_app("Product Price")
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param(f"customer_purchase_follow_up.dp.{app}", "7")

        float_field = self._float_field(related_digits=app, digits=(10, 5))

        with patch.object(dp_fields_mod, "_is_ddp_installed", return_value=True):
            desc = float_field.get_description(self.env)
            self.assertEqual(desc.get("digits"), (10, 5))  # unchanged

    def test_skips_when_module_not_installed(self):
        """Do not inject when the module is reported as not installed."""
        app = _unique_app("Product Price")
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param(f"customer_purchase_follow_up.dp.{app}", "4")

        float_field = self._float_field(related_digits=app)

        with patch.object(dp_fields_mod, "_is_ddp_installed", return_value=False):
            desc = float_field.get_description(self.env)
            # No injection -> digits is absent/falsy
            self.assertFalse(desc.get("digits"))

    def test_clamps_scale_to_safe_range(self):
        """Clamp scale to [0, 12] even if the parameter is out of range."""
        icp = self.env["ir.config_parameter"].sudo()

        # High value -> clamp to 12
        app_high = _unique_app("Product Price")
        icp.set_param(f"customer_purchase_follow_up.dp.{app_high}", "99")
        field_high = self._float_field(related_digits=app_high)
        with patch.object(dp_fields_mod, "_is_ddp_installed", return_value=True):
            desc_high = field_high.get_description(self.env)
            self.assertEqual(desc_high.get("digits"), (16, 12))

        # Negative -> clamp to 0
        app_low = _unique_app("Product Price")
        icp.set_param(f"customer_purchase_follow_up.dp.{app_low}", "-5")
        field_low = self._float_field(related_digits=app_low)
        with patch.object(dp_fields_mod, "_is_ddp_installed", return_value=True):
            desc_low = field_low.get_description(self.env)
            self.assertEqual(desc_low.get("digits"), (16, 0))

    def test_invalid_parameter_falls_back_to_default(self):
        """If the stored parameter is not an int, fall back to default scale=2."""
        app = _unique_app("Product Price")
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param(f"customer_purchase_follow_up.dp.{app}", "not_an_int")

        float_field = self._float_field(related_digits=app)

        with patch.object(dp_fields_mod, "_is_ddp_installed", return_value=True):
            desc = float_field.get_description(self.env)
            self.assertEqual(desc.get("digits"), (16, 2))

    # ------------------------
    # Non-float and missing marker
    # ------------------------
    def test_does_not_affect_non_float_or_missing_marker(self):
        """No injection on non-float fields or floats lacking _related__digits."""
        app = _unique_app("Irrelevant")
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param(f"customer_purchase_follow_up.dp.{app}", "4")

        # Non-float field - asignar atributos mínimos
        char_field = fields.Char()
        char_field.name = "x_test_char"
        char_field.model_name = "x.test.model"
        char_field.string = "Test Char"

        with patch.object(dp_fields_mod, "_is_ddp_installed", return_value=True):
            desc_char = char_field.get_description(self.env)
            self.assertFalse(desc_char.get("digits"))

        # Float without the marker
        float_field = self._float_field()  # Esto ya asigna los atributos necesarios
        with patch.object(dp_fields_mod, "_is_ddp_installed", return_value=True):
            desc_float = float_field.get_description(self.env)
            self.assertFalse(desc_float.get("digits"))

    # ------------------------
    # Uninstall behavior
    # ------------------------
    def test_uninstall_hook_restores_original_method(self):
        """uninstall_hook must restore the original Field.get_description."""
        app = _unique_app("Product Price")
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param(f"customer_purchase_follow_up.dp.{app}", "3")

        float_field = self._float_field(related_digits=app)

        with patch.object(dp_fields_mod, "_is_ddp_installed", return_value=True):
            desc_before = float_field.get_description(self.env)
            self.assertEqual(desc_before.get("digits"), (16, 3))

        # Call the uninstall hook: should restore original method
        dp_fields_mod.uninstall_hook(self.env.cr, self.env.registry)

        # After uninstall, the injection should no longer happen
        desc_after = float_field.get_description(self.env)
        self.assertFalse(desc_after.get("digits"))
