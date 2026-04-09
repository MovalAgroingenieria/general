# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.base_assembly.models.res_company import (
    _ASSEMBLY_COMPANY_DEFAULT_CONFIG_REFS,
)
from odoo.tests import TransactionCase


class TestResCompanyAssemblyTemplateDefaults(TransactionCase):
    def test_ensure_default_templates_fills_empty_fields(self):
        company = self.env.company
        clear_vals = {
            fname: False for fname, _xml in _ASSEMBLY_COMPANY_DEFAULT_CONFIG_REFS
        }
        company.write(clear_vals)
        company._assembly_ensure_default_template_configuration()
        for field_name, xmlid in _ASSEMBLY_COMPANY_DEFAULT_CONFIG_REFS:
            self.assertEqual(
                getattr(company, field_name),
                self.env.ref(xmlid),
                field_name,
            )

    def test_ensure_default_templates_preserves_custom_mail_template(self):
        company = self.env.company
        default_pub = self.env.ref(
            "base_assembly.mail_template_assembly_publication_default"
        )
        custom_pub = default_pub.copy({"name": "Custom publication template (test)"})
        company.write(
            {
                "assembly_default_publication_mail_template_id": custom_pub.id,
            }
        )
        clear_vals = {
            fname: False
            for fname, _xml in _ASSEMBLY_COMPANY_DEFAULT_CONFIG_REFS
            if fname != "assembly_default_publication_mail_template_id"
        }
        company.write(clear_vals)
        company._assembly_ensure_default_template_configuration()
        self.assertEqual(
            company.assembly_default_publication_mail_template_id,
            custom_pub,
        )
        for field_name, xmlid in _ASSEMBLY_COMPANY_DEFAULT_CONFIG_REFS:
            if field_name == "assembly_default_publication_mail_template_id":
                continue
            self.assertEqual(
                getattr(company, field_name),
                self.env.ref(xmlid),
                field_name,
            )

    def test_new_company_create_receives_default_templates(self):
        company = self.env["res.company"].create(
            {
                "name": "Assembly template defaults co",
                "currency_id": self.env.company.currency_id.id,
            }
        )
        for field_name, xmlid in _ASSEMBLY_COMPANY_DEFAULT_CONFIG_REFS:
            self.assertEqual(
                getattr(company, field_name),
                self.env.ref(xmlid),
                field_name,
            )
