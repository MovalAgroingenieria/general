# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import MissingError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStreetTypeSettings(TransactionCase):

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        cls.Config = cls.env["res.config.settings"]
        cls.IrConfig = cls.env["ir.config_parameter"]
        cls.IrView = cls.env["ir.ui.view"]

        # Ensure the company has a country for the address_format test
        country_es = cls.env["res.country"].search([("code", "=", "ES")], limit=1)
        if not country_es:
            raise MissingError(
                cls.env._("Country 'ES' not found in the test environment.")
            )
        cls.env.company.country_id = country_es

        # XML IDs used by your views/actions
        cls.view_tree_cfg = cls.env.ref(
            "partner_address_street_type.res_street_type_config_view_tree"
        )
        cls.view_tree_simple = cls.env.ref(
            "partner_address_street_type.res_street_type_view_tree"
        )
        cls.view_settings_form = cls.env.ref(
            "partner_address_street_type.res_config_settings_view_form_general_settings"
        )

    def test_action_open_street_types_returns_expected_view(self):
        """open_street_types must return the forced 'tree' view set in the method."""
        wizard = self.Config.create({})
        action = wizard.open_street_types()
        self.assertEqual(action["type"], "ir.actions.act_window")
        # It must force the 'tree' view to res_street_type_config_view_tree
        self.assertIn("views", action)
        self.assertEqual(action["views"][0][1], "tree")
        self.assertEqual(action["views"][0][0], self.view_tree_cfg.id)

    def test_set_values_updates_country_address_format(self):
        """
        set_values must update the address_format of the company's country
        using the provided address_format_set value.
        """
        original = self.env.company.country_id.address_format
        try:
            new_format = (
                "%(street_type)s %(street)s\n%(zip)s %(city)s\n%(country_name)s"
            )
            wizard = self.Config.create(
                {
                    "address_format_set": new_format,
                }
            )
            wizard.set_values()
            # Re-read country to pick up changes
            self.env.company.country_id.invalidate_recordset(["address_format"])
            updated = self.env.company.country_id.address_format
            self.assertEqual(updated, new_format)
        finally:
            # Restore original value to avoid side effects on other tests
            self.env.company.country_id.address_format = original

    def test_config_parameter_street_type_shown(self):
        """
        The Selection field with config_parameter must persist and read correctly.
        """
        # Default value (as defined in your model): 'long'
        wizard_default = self.Config.create({})
        self.assertEqual(wizard_default.street_type_shown, "long")

        # Change to 'short' and verify the parameter is persisted
        key = "partner_address_street_type.street_type_shown"
        wizard = self.Config.create({"street_type_shown": "short"})
        wizard.execute()  # executes set_values internally
        param_val = self.IrConfig.get_param(key)
        self.assertEqual(param_val, "short")

        # Change back to 'long'
        wizard2 = self.Config.create({"street_type_shown": "long"})
        wizard2.execute()
        param_val2 = self.IrConfig.get_param(key)
        self.assertEqual(param_val2, "long")
