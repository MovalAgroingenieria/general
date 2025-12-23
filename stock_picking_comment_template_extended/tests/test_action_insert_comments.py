# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from unittest.mock import PropertyMock, patch

from odoo.tests.common import TransactionCase
from odoo.tools import html2plaintext


class FakeTemplate:
    """Lightweight object to simulate a template record."""

    def __init__(self, position, name):
        self.position = position
        self.name = name


class TestActionInsertComments(TransactionCase):

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
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

    def test_no_templates_clears_fields_and_does_not_render(self):
        """If there are no templates, the method clears both comment fields."""
        picking_cls = self.picking.__class__

        with patch.object(
            picking_cls, "comment_template_ids", new_callable=PropertyMock
        ) as mock_templates, patch.object(
            picking_cls, "render_comment", autospec=True, return_value=""
        ) as mock_render:
            mock_templates.return_value = []

            # Preload values and verify they get cleared
            self.picking.write(
                {"top_comment": "<p>OLD</p>", "bottom_comment": "<p>OLD</p>"}
            )

            self.picking.action_insert_comments()

            top_txt = html2plaintext(self.picking.top_comment or "").strip()
            bottom_txt = html2plaintext(self.picking.bottom_comment or "").strip()

            self.assertEqual(top_txt, "")
            self.assertEqual(bottom_txt, "")
            mock_render.assert_not_called()

    def test_templates_render_and_split_top_bottom_using_partner_language(self):
        """Templates are rendered and split into top/bottom
        using partner language context."""
        fake_top_1 = FakeTemplate(position="before_lines", name="Top A")
        fake_top_2 = FakeTemplate(position="before_lines", name="Top B")
        fake_bottom = FakeTemplate(position="after_lines", name="Bottom X")
        fake_templates = [fake_top_1, fake_bottom, fake_top_2]

        def fake_render(picking, template):
            # Ensure the partner language is applied through the picking context
            lang = picking.env.context.get("lang")
            return f"[{lang}] {template.name}"

        picking_cls = self.picking.__class__

        with patch.object(
            picking_cls, "comment_template_ids", new_callable=PropertyMock
        ) as mock_templates, patch.object(
            picking_cls, "render_comment", autospec=True, side_effect=fake_render
        ) as mock_render:
            mock_templates.return_value = fake_templates

            self.picking.write({"top_comment": False, "bottom_comment": False})
            self.picking.action_insert_comments()

            self.assertEqual(mock_render.call_count, len(fake_templates))

            top_txt = html2plaintext(self.picking.top_comment or "").strip()
            bottom_txt = html2plaintext(self.picking.bottom_comment or "").strip()

            # Order must be preserved: Top A, Bottom X, Top B (split by position)
            expected_top = "[es_ES] Top A[es_ES] Top B"
            expected_bottom = "[es_ES] Bottom X"

            self.assertEqual(top_txt, expected_top)
            self.assertEqual(bottom_txt, expected_bottom)
