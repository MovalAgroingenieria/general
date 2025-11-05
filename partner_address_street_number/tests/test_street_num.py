# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase, tagged
from odoo import api


@tagged("post_install", "-at_install")  # run after install; faster local runs
class TestPartnerStreetNum(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Partner = self.env["res.partner"]
        self.Country = self.env["res.country"]
        self.Company = self.env["res.company"]

        # Ensure we have a country and company relationship to control address_format
        # Prefer ES; if not found, create a dummy country with ES code.
        self.es = self.Country.search([("code", "=", "ES")], limit=1)
        if not self.es:
            self.es = self.Country.create({"name": "Spain (Test)", "code": "ES"})

        # Put main company on ES to align with hooks' default fallback behavior
        self.env.company.write({"country_id": self.es.id})

    # ---------- Model integration -------------------------------------------

    def test_field_is_present(self):
        # 1) Field exists on res.partner
        self.assertIn("street_num", self.Partner._fields, "street_num field must exist on res.partner")

    def test_address_fields_includes_street_num(self):
        # 2) street_num is part of address propagation fields
        names = self.Partner._address_fields()
        # normalize to list
        names_norm = list(names) if not isinstance(names, (list, set, tuple)) else list(names)
        self.assertIn("street_num", names_norm, "street_num must be included in _address_fields")

    def test_formatting_address_fields_includes_street_num(self):
        # 3) v17+ address formatting placeholders include street_num (fallback safe)
        parent = getattr(self.Partner, "_formatting_address_fields", None)
        self.assertTrue(callable(parent), "_formatting_address_fields should exist on v18")
        names = self.Partner._formatting_address_fields()
        names_norm = list(names) if not isinstance(names, (list, set, tuple)) else list(names)
        self.assertIn("street_num", names_norm, "street_num must be allowed in address_format placeholders")

    # ---------- Display and formatting --------------------------------------

    def test_display_address_includes_street_num(self):
        # Ensure country format uses %(street)s %(street_num)s
        self.es.write({"address_format": "%(street)s %(street_num)s\n%(zip)s %(city)s\n%(country_name)s"})
        p = self.Partner.create({
            "name": "Moval Test",
            "street": "Main St",
            "street_num": "42",
            "zip": "28000",
            "city": "Madrid",
            "country_id": self.es.id,
        })
        rendered = p._display_address()
        self.assertIn("Main St 42", rendered, "Rendered address must include street + street_num")
        self.assertIn("28000 Madrid", rendered)

    # ---------- Hook behavior ------------------------------------------------

    def test_post_init_hook_injects_token(self):
        """
        Simulate post_init_hook behavior:
        - Remove any token from country format
        - Call the hook
        - Expect token injected
        """
        # Ensure exported hook is importable from module namespace
        # Adjust the import path if your hook file/module name differs.
        from odoo.addons.partner_address_street_number import hooks as streetnum_hooks

        baseline = "%(street)s\n%(zip)s %(city)s\n%(country_name)s"
        self.es.write({"address_format": baseline})

        # Call hook with v18 signature (env); also compatible with our coercion helper.
        streetnum_hooks.post_init_hook(self.env)

        self.es.invalidate_recordset(["address_format"])
        self.assertIn(
            "%(street_num)s",
            self.es.address_format,
            "post_init_hook must inject %(street_num)s into ES address_format",
        )

    # ---------- Context defaults --------------------------------------------

    def test_default_street_num_context_on_create(self):
        """
        We can’t “click UI” here, but we can assert that a record created
        with default_street_num in the context receives the value.
        """
        ctx = dict(self.env.context, default_street_num="99")
        p = self.Partner.with_context(ctx).create({
            "name": "Child Address",
            "type": "other",
            "parent_id": self.env.company.partner_id.id,
            "street": "Gran Via",
            "country_id": self.es.id,
        })
        self.assertEqual(p.street_num, "99", "default_street_num must initialize street_num on create via context")

