# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from unittest.mock import patch

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAccountMoveComments(TransactionCase):
    """Tests for the comment insertion logic on account.move."""

    @classmethod
    def setUpClass(cls):  # pylint: disable=invalid-name
        super().setUpClass()

        cls.AccountMove = cls.env["account.move"]
        cls.Partner = cls.env["res.partner"]
        cls.Journal = cls.env["account.journal"]

        cls.company = cls.env.company

        # Partner with a specific language to verify the lang in context
        cls.partner = cls.Partner.create(
            {
                "name": "Test Partner",
                "lang": "es_ES",
            }
        )

        # Ensure we have a general journal (no need for sale/purchase)
        cls.journal = cls.Journal.search([("type", "=", "general")], limit=1)
        if not cls.journal:
            journal_vals = {
                "name": "Test General Journal",
                "code": "TGEN",
                "type": "general",
            }
            if "company_id" in cls.Journal._fields:
                journal_vals["company_id"] = cls.company.id
            elif "company_ids" in cls.Journal._fields:
                journal_vals["company_ids"] = [(4, cls.company.id)]
            cls.journal = cls.Journal.create(journal_vals)

        # Dynamically get the comodel of comment_template_ids
        comment_field = cls.AccountMove._fields.get("comment_template_ids")
        if not comment_field:
            raise AssertionError(
                "The field 'comment_template_ids' must exist on account.move "
                "for this test to run."
            )
        cls.CommentTemplate = cls.env[comment_field.comodel_name]

        # Mark account.move as supporting comment templates (base_comment_template
        # constraint _check_models requires ir.model.is_comment_template = True)
        cls.env.ref("account.model_account_move").is_comment_template = True

        # Create two templates with different positions
        cls.template_top = cls.CommentTemplate.create(
            {
                "name": "Top Template",
                "position": "before_lines",
                "text": "my text",
                "models": "account.move",
            }
        )
        cls.template_bottom = cls.CommentTemplate.create(
            {
                "name": "Bottom Template",
                "position": "after_lines",
                "text": "my text",
                "models": "account.move",
            }
        )

        # Create a minimal move for testing (no lines, no accounting constraints)
        cls.move = cls.AccountMove.create(
            {
                "move_type": "entry",
                "journal_id": cls.journal.id,
                "partner_id": cls.partner.id,
                "comment_template_ids": [
                    (6, 0, [cls.template_top.id, cls.template_bottom.id])
                ],
            }
        )

    def test_action_insert_comments_splits_by_position(self):
        """Templates are split into top_comment and bottom_comment by position."""
        move = self.move

        # We patch render_comment to control the output per template.
        def fake_render_comment(_self_move, template):
            if template == self.template_top:
                return "TOP-HTML;"
            if template == self.template_bottom:
                return "BOTTOM-HTML;"
            return ""

        with patch.object(
            type(move), "render_comment", autospec=True, side_effect=fake_render_comment
        ):
            move.action_insert_comments()

        # Html fields are stored as Markup and may add <p> wrappers,
        # so we just check that our text is present in the rendered HTML.
        self.assertIn(
            "TOP-HTML;",
            str(move.top_comment),
            "Top template should be rendered into top_comment.",
        )
        self.assertIn(
            "BOTTOM-HTML;",
            str(move.bottom_comment),
            "Bottom template should be rendered into bottom_comment.",
        )

    def test_action_insert_comments_uses_partner_language(self):
        """render_comment must be called with the partner language in context."""
        move = self.move
        seen_langs = []

        def fake_render_comment(_self_move, template):
            # Capture the lang used in the template's environment context
            seen_langs.append(template.env.context.get("lang"))
            return "DUMMY"

        with patch.object(
            type(move), "render_comment", autospec=True, side_effect=fake_render_comment
        ):
            move.action_insert_comments()

        self.assertTrue(
            seen_langs, "render_comment should have been called at least once."
        )
        self.assertTrue(
            all(lang == self.partner.lang for lang in seen_langs),
            "render_comment must be called with the partner language in context.",
        )
