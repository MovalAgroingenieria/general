from unittest.mock import PropertyMock, patch

from odoo.tests.common import TransactionCase
from odoo.tools import html2plaintext


class FakeTemplate:
    def __init__(self, position, name):
        self.position = position
        self.name = name

    def with_context(self, **_kwargs):
        return self


class TestActionInsertComments(TransactionCase):

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()  # <-- nombre correcto
        cls.partner = cls.env["res.partner"].create(
            {"name": "Test Partner", "lang": "es_ES"}
        )
        cls.picking = cls.env["stock.picking"].create(
            {
                "picking_type_id": cls.env.ref("stock.picking_type_out").id,
                "location_id": cls.env.ref("stock.stock_location_stock").id,
                "location_dest_id": cls.env.ref("stock.stock_location_customers").id,
                "partner_id": cls.partner.id,
                "origin": "TEST/COMMENTS",
            }
        )

    def test_no_templates_does_nothing_and_clears_fields(self):
        with patch.object(
            type(self.picking), "comment_template_ids", new_callable=PropertyMock
        ) as mock_templates, patch.object(
            type(self.picking), "render_comment", autospec=True, return_value=""
        ) as mock_render:
            mock_templates.return_value = []
            # precargar valores para verificar que se vacían
            self.picking.write({"top_comment": "OLD", "bottom_comment": "OLD"})

            self.picking.action_insert_comments()

            top_txt = html2plaintext(self.picking.top_comment or "").strip()
            bottom_txt = html2plaintext(self.picking.bottom_comment or "").strip()
            self.assertEqual(top_txt, "")
            self.assertEqual(bottom_txt, "")
            mock_render.assert_not_called()

    def test_templates_render_and_split_top_bottom_with_lang(self):
        fake_top_1 = FakeTemplate(position="before_lines", name="Top A")
        fake_top_2 = FakeTemplate(position="before_lines", name="Top B")
        fake_bottom = FakeTemplate(position="after_lines", name="Bottom X")
        fake_templates = [fake_top_1, fake_bottom, fake_top_2]

        def fake_render(_self, template):
            # comprueba que usa el idioma del partner
            return f"[{self.picking.partner_id.lang}] {template.name}"

        with patch.object(
            type(self.picking), "comment_template_ids", new_callable=PropertyMock
        ) as mock_templates, patch.object(
            type(self.picking), "render_comment", autospec=True, side_effect=fake_render
        ) as mock_render:
            mock_templates.return_value = fake_templates

            self.picking.write({"top_comment": "", "bottom_comment": ""})
            self.picking.action_insert_comments()

            self.assertEqual(mock_render.call_count, len(fake_templates))

            # normaliza HTML -> texto plano para comparar contenido
            top_txt = html2plaintext(self.picking.top_comment or "").strip()
            bottom_txt = html2plaintext(self.picking.bottom_comment or "").strip()

            expected_top = "[es_ES] Top A[es_ES] Top B"
            expected_bottom = "[es_ES] Bottom X"
            self.assertEqual(top_txt, expected_top)
            self.assertEqual(bottom_txt, expected_bottom)
