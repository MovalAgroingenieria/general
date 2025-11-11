# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=invalid-name
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.misc import str2bool

PARAM_KEY = "hr_expense_activities.with_activity"


@tagged("post_install", "-at_install")
class TestResConfigSettings(TransactionCase):
    def setUp(self):
        super().setUp()
        self.icp = self.env["ir.config_parameter"].sudo()
        # Start each test from a clean slate
        self.icp.set_param(PARAM_KEY, None)

    def _get_bool_param(self):
        """Return the config param as a strict boolean,
        regardless of backend representation."""
        val = self.icp.get_param(PARAM_KEY, default="False")
        return str2bool(str(val))

    def test_default_is_false_when_param_unset(self):
        """When the ICP is not set, the settings field should default to False."""
        settings = self.env["res.config.settings"].create({})
        # The field mirrors the config parameter; unset -> False
        self.assertFalse(settings.with_activity)

    def test_execute_true_persists_to_icp(self):
        settings = self.env["res.config.settings"].create({"with_activity": True})
        settings.execute()

        # antes: self.assertEqual(self.icp.get_param(PARAM_KEY), "True")
        self.assertTrue(self._get_bool_param())

        settings2 = self.env["res.config.settings"].create({})
        self.assertTrue(settings2.with_activity)

    def test_toggle_back_to_false(self):
        s1 = self.env["res.config.settings"].create({"with_activity": True})
        s1.execute()
        # antes: self.assertEqual(self.icp.get_param(PARAM_KEY), "True")
        self.assertTrue(self._get_bool_param())

        s2 = self.env["res.config.settings"].create({"with_activity": False})
        s2.execute()
        # antes: self.assertEqual(self.icp.get_param(PARAM_KEY), "False")
        self.assertFalse(self._get_bool_param())

        s3 = self.env["res.config.settings"].create({})
        self.assertFalse(s3.with_activity)
