# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from unittest.mock import patch

from odoo.tests.common import SavepointCase, tagged


@tagged("post_install", "-at_install")
class TestReportLabelAssociatedView(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ActionsServer = cls.env["ir.actions.server"]
        cls.UIView = cls.env["ir.ui.view"]
        cls.ActWindow = cls.env["ir.actions.act_window"]

        # Crear una vista QWeb dummy con key = xmlid y nombre reconocible
        # key es el XMLID lógico (module.name). No hace falta que exista el módulo real para la prueba.
        cls.test_module = "x_test_mod"
        cls.template_name = "label_template_demo"
        cls.xmlid_key = f"{cls.test_module}.{cls.template_name}"

        cls.qweb_view = cls.UIView.create(
            {
                "name": cls.template_name,
                "type": "qweb",
                "key": cls.xmlid_key,
                "arch_db": "<t t-name='%s'><t t-esc=\"'ok'\"/></t>" % cls.xmlid_key,
            }
        )

        # Crear un ir.actions.server con la label_template que apunte a esa vista
        cls.action_server = cls.ActionsServer.create(
            {
                "name": "Test Report Label Associated View",
                "state": "code",
                "model_id": cls.env.ref("base.model_res_partner").id,
                "code": "action = records.report_label_associated_view()",
                "label_template": cls.xmlid_key,
            }
        )

    def test_happy_path_returns_action_with_domain(self):
        """Should return an act_window dict that filters QWeb views by name or exact key."""
        res = self.action_server.report_label_associated_view()
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("res_model"), "ir.ui.view")

        # Verificar dominio esperado
        expected_domain = [
            ("type", "=", "qweb"),
            "|",
            ("name", "ilike", self.template_name),
            ("key", "=", self.xmlid_key),
        ]
        self.assertEqual(res.get("domain"), expected_domain)

        # Asegurar que view_mode tenga lista y formulario
        self.assertIn("list", res.get("view_mode", ""))
        self.assertIn("form", res.get("view_mode", ""))

    def test_invalid_label_returns_false(self):
        """If label_template lacks the 'module.name' format, method should return False."""
        srv = self.action_server.copy({"label_template": "invalid_without_dot"})
        self.assertFalse(srv.report_label_associated_view())

        srv2 = self.action_server.copy({"label_template": ""})
        self.assertFalse(srv2.report_label_associated_view())

    def test_fallback_when_xmlid_missing(self):
        """
        If _for_xml_id('base.action_ui_view') fails, method should fallback to any act_window
        that opens ir.ui.view, without raising.
        """
        # Asegurar que existe al menos una acción que abre ir.ui.view (por si acaso)
        aw = self.ActWindow.search([("res_model", "=", "ir.ui.view")], limit=1)
        if not aw:
            aw = self.ActWindow.create(
                {
                    "name": "Views",
                    "res_model": "ir.ui.view",
                    "view_mode": "list,form",
                }
            )

        with patch.object(
            type(self.ActWindow), "_for_xml_id", side_effect=Exception("missing")
        ):
            res = self.action_server.report_label_associated_view()
            self.assertIsInstance(res, dict)
            self.assertEqual(res.get("res_model"), "ir.ui.view")
            self.assertIn("domain", res)
