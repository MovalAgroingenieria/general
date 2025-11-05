# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from lxml import etree
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestChildIdsMergedContext(TransactionCase):
    def setUp(self):  # pylint: disable=invalid-name
        super().setUp()
        self.partner_obj = self.env["res.partner"]
        self.base_form = self.env.ref("base.view_partner_form")

    def _get_partner_form_arch(self):
        """Return fully combined arch via get_view (v18 API)."""
        view_info = self.partner_obj.get_view(
            view_id=self.base_form.id, view_type="form"
        )
        return view_info["arch"]

    def _get_child_ids_context(self, arch_xml: str) -> str:
        doc = etree.fromstring(
            arch_xml.encode("utf-8")
        )  # pylint: disable=c-extension-no-member
        nodes = doc.xpath("//form//field[@name='child_ids']")
        self.assertTrue(
            nodes, "child_ids field not found in the resolved partner form view"
        )
        return nodes[0].get("context") or ""

    def test_child_ids_context_contains_both_defaults(self):
        arch = self._get_partner_form_arch()
        ctx = self._get_child_ids_context(arch)

        # Base defaults
        self.assertIn("'default_parent_id': id", ctx)
        self.assertIn("'default_type': 'other'", ctx)

        # Merged by the bridge
        self.assertIn(
            "'default_street_num': street_num",
            ctx,
            "Merged context must include default_street_num",
        )
        self.assertIn(
            "'default_street_type_id': street_type_id",
            ctx,
            "Merged context must include default_street_type_id",
        )
