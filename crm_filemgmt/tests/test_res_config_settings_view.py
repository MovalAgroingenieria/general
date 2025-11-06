# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import unittest

from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval

try:
    from odoo.tests.common import SavepointCase as BaseCase
except ImportError:
    BaseCase = TransactionCase


class TestResConfigSettingsView(BaseCase):
    """Tests for crm_filemgmt settings view, action and menu (no combined arch)."""

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.View = cls.env["ir.ui.view"].sudo()
        cls.Menu = cls.env["ir.ui.menu"].sudo()
        cls.Action = cls.env["ir.actions.act_window"].sudo()

        # Resolve external IDs; skip suite if not installed
        cls.view_inherit = cls.env.ref(
            "crm_filemgmt.res_config_settings_view_form", raise_if_not_found=False
        )
        cls.action_settings = cls.env.ref(
            "crm_filemgmt.action_res_config_settings_files", raise_if_not_found=False
        )
        cls.menu_parameters = cls.env.ref(
            "crm_filemgmt.menu_parameters", raise_if_not_found=False
        )

        if not all([cls.view_inherit, cls.action_settings, cls.menu_parameters]):
            raise unittest.SkipTest("Settings XML not installed (view/action/menu).")

    # -------------------------
    # Action tests
    # -------------------------

    def test_action_properties(self):
        """The action should open res.config.settings inline,
        form mode, with module context."""
        act = self.action_settings
        self.assertEqual(act.res_model, "res.config.settings")
        self.assertEqual(act.view_mode, "form")
        self.assertEqual(act.target, "inline")

        # Context is a python-literal string in DB; parse it safely
        ctx_raw = act.context or "{}"
        ctx = safe_eval(ctx_raw, {})
        # Expect module context pointing at our module
        self.assertIn("module", ctx)
        self.assertIn("crm_filemgmt", str(ctx.get("module")))

        # The action should explicitly use our inherited view
        self.assertEqual(act.view_id.id, self.view_inherit.id)

    # -------------------------
    # Menu tests
    # -------------------------

    def test_menu_points_to_action(self):
        """Menu 'Parameters' should point to our settings action under configuration."""
        menu = self.menu_parameters
        self.assertEqual(menu.action.id, self.action_settings.id)

        parent = menu.parent_id
        self.assertTrue(parent, "Parameters menu should have a parent (configuration).")

        expected_parent = self.env.ref(
            "crm_filemgmt.menu_configuration", raise_if_not_found=False
        )
        if expected_parent:
            self.assertEqual(parent.id, expected_parent.id)
        else:
            # Fallback: ensure the parent has an external id at all
            parent_xids = parent.get_external_id()
            self.assertTrue(
                parent_xids.get(parent.id),
                "Parent menu has no external id to verify against.",
            )

    def test_open_action_via_client_like(self):
        """Simulate opening the action to ensure it is accessible and
        returns a window action dict."""
        action_dict = self.Action.browse(self.action_settings.id).read()[0]
        self.assertEqual(action_dict.get("type"), "ir.actions.act_window")
        self.assertEqual(action_dict.get("res_model"), "res.config.settings")
        self.assertIn("form", action_dict.get("view_mode", ""))


if __name__ == "__main__":
    unittest.main()
