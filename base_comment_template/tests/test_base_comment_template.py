# Copyright 2020 NextERP Romania SRL
# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools.misc import mute_logger

from .fake_models import ResUsers, setup_test_model, teardown_test_model


class TestCommentTemplate(TransactionCase):
    """Tests for the base_comment_template module."""

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()
        # Register the test model that inherits from comment.template
        setup_test_model(cls.env, ResUsers)

        cls.user_obj = cls.env.ref("base.model_res_users")
        # Mark res.users as supporting comment templates
        cls.user_obj.is_comment_template = True

        cls.user = cls.env.ref("base.user_demo")
        cls.user2 = cls.env.ref("base.demo_user0")
        cls.partner_id = cls.env.ref("base.res_partner_12")
        cls.partner2_id = cls.env.ref("base.res_partner_10")
        cls.ResPartnerTitle = cls.env["res.partner.title"]
        cls.main_company = cls.env.ref("base.main_company")

        # Company used to scope templates
        cls.company = cls.env["res.company"].create(
            {
                "name": "Test company",
                # Add extra required company fields here if needed in your DB
                # e.g. "manufacturing_lead": cls.main_company.manufacturing_lead,
            }
        )

        cls.before_template_id = cls.env["base.comment.template"].create(
            {
                "name": "Top template",
                "text": "Text before lines",
                "models": cls.user_obj.model,
                "company_id": cls.company.id,
            }
        )
        cls.after_template_id = cls.env["base.comment.template"].create(
            {
                "name": "Bottom template",
                "position": "after_lines",
                "text": "Text after lines",
                "models": cls.user_obj.model,
                "company_id": cls.company.id,
            }
        )

        cls.user.partner_id.base_comment_template_ids = [
            (4, cls.before_template_id.id),
            (4, cls.after_template_id.id),
        ]

    @classmethod
    def tearDownClass(cls):  # pylint: disable=invalid-name
        teardown_test_model(cls.env, ResUsers)
        return super(TestCommentTemplate, cls).tearDownClass()

    # -------------------------------------------------------------------------
    # Template / model linking
    # -------------------------------------------------------------------------

    def test_template_model_ids(self):
        """Templates should be linked to the selected model."""
        self.assertIn(
            self.user_obj.model, self.before_template_id.mapped("model_ids.model")
        )
        self.assertEqual(len(self.before_template_id.model_ids), 1)
        self.assertIn(
            self.user_obj.model, self.after_template_id.mapped("model_ids.model")
        )
        self.assertEqual(len(self.after_template_id.model_ids), 1)

    def test_template_models_constrains(self):
        """Constraint should block non-existing / non-allowed models."""
        with self.assertRaises(ValidationError):
            self.env["base.comment.template"].create(
                {
                    "name": "Custom template",
                    "text": "Text",
                    "models": "incorrect.model",
                    "company_id": self.company.id,
                }
            )

    # -------------------------------------------------------------------------
    # comment.template mixin behaviour
    # -------------------------------------------------------------------------

    def test_general_template(self):
        """Partner-specific templates should be computed for the record."""
        # Force compute (normally triggered when partner_id changes)
        self.user._compute_comment_template_ids()  # pylint: disable=protected-access
        # Check that the default templates are included
        self.assertIn(self.before_template_id, self.user.comment_template_ids)
        self.assertIn(self.after_template_id, self.user.comment_template_ids)

    def test_global_template(self):
        """Global templates should apply even if not set on the partner."""
        # Non-global template
        global_template = self.env["base.comment.template"].create(
            {
                "name": "Top template",
                "text": "Text before lines",
                "models": self.user_obj.model,
                "company_id": self.company.id,
            }
        )
        self.user._compute_comment_template_ids()  # pylint: disable=protected-access
        self.assertNotIn(global_template, self.user.comment_template_ids)

        # When marked as global, it should appear
        global_template.global_template = True
        self.user._compute_comment_template_ids()  # pylint: disable=protected-access
        self.assertIn(global_template, self.user.comment_template_ids)

    def test_partner_template(self):
        """Templates can be manually linked to a partner."""
        self.partner2_id.base_comment_template_ids = [
            (4, self.before_template_id.id),
            (4, self.after_template_id.id),
        ]
        self.assertIn(
            self.before_template_id, self.partner2_id.base_comment_template_ids
        )
        self.assertIn(
            self.after_template_id, self.partner2_id.base_comment_template_ids
        )

    def test_partner_template_domain(self):
        """Domain on the template should filter applicable partners."""
        self.partner2_id.base_comment_template_ids = [
            (4, self.before_template_id.id),
            (4, self.after_template_id.id),
        ]
        # Domain that filters by the specific user id
        self.before_template_id.domain = "[('id', 'in', %s)]" % self.user.ids

        self.assertIn(
            self.before_template_id, self.partner2_id.base_comment_template_ids
        )
        self.assertNotIn(
            self.before_template_id, self.partner_id.base_comment_template_ids
        )

    # -------------------------------------------------------------------------
    # render_comment
    # -------------------------------------------------------------------------

    def test_render_comment_text(self):
        """Basic template rendering using object fields."""
        expected_text = "Test comment render %s" % self.user.name
        self.before_template_id.text = "Test comment render {{object.name}}"

        # Render as the default test user (admin in tests)
        result = self.user.render_comment(self.before_template_id)
        self.assertEqual(result, expected_text)

    def test_render_comment_text_(self):
        """Template rendering with translations and related fields."""
        ro_ro_lang = (
            self.env["res.lang"]
            .with_context(active_test=False)
            .search([("code", "=", "ro_RO")])
        )
        with mute_logger("odoo.addons.base.models.ir_translation"):
            self.env["base.language.install"].create(
                {"overwrite": True, "lang_ids": [(6, 0, [ro_ro_lang.id])]}
            ).lang_install()

        module = self.env.ref("base.module_test_translation_import")
        export = self.env["base.language.export"].create(
            {"lang": "ro_RO", "format": "po", "modules": [Command.set([module.id])]}
        )
        export.act_getfile()
        po_file = export.data
        self.assertIsNotNone(po_file)

        partner_title = self.ResPartnerTitle.create(
            {"name": "Ambassador", "shortcut": "Amb."}
        )
        ctx = {"lang": "ro_RO"}
        partner_title.with_context(**ctx).write(
            {"name": "Ambasador", "shortcut": "Amb."}
        )
        self.user.partner_id.title = partner_title
        self.before_template_id.text = "Test comment render {{object.title.name}}"

        expected_en_text = "Test comment render Ambassador"
        expected_ro_text = "Test comment render Ambasador"

        # Render without language context (English)
        result_en = self.user.render_comment(self.before_template_id)
        self.assertEqual(result_en, expected_en_text)

        # Render with ro_RO language context
        result_ro = self.user.with_context(**ctx).render_comment(
            self.before_template_id
        )
        self.assertEqual(result_ro, expected_ro_text)

    # -------------------------------------------------------------------------
    # Wizard / partner integration
    # -------------------------------------------------------------------------

    def test_partner_template_wizaard(self):
        """Wizard should have defaults and at least one target model option."""
        partner_preview = (
            self.env["base.comment.template.preview"]
            .with_context(default_base_comment_template_id=self.before_template_id.id)
            .create({})
        )
        self.assertTrue(partner_preview)

        default = (
            self.env["base.comment.template.preview"]
            .with_context(default_base_comment_template_id=self.before_template_id.id)
            .default_get(partner_preview._fields)
        )
        self.assertTrue(default.get("base_comment_template_id"))

        # pylint: disable=protected-access
        resource_ref = partner_preview._selection_target_model()
        # In v18 it is enough to ensure there is at least one option
        self.assertTrue(len(resource_ref) >= 1)

        partner_preview._compute_no_record()  # pylint: disable=protected-access
        self.assertTrue(partner_preview.no_record)

    def test_partner_commercial_fields(self):
        """Commercial fields of partners should include comment templates."""
        # pylint: disable=protected-access
        self.assertIn(
            "base_comment_template_ids",
            self.env["res.partner"]._commercial_fields(),
        )
