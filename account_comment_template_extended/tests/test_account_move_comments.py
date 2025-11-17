# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from unittest.mock import patch

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAccountMoveComments(TransactionCase):
    """Tests for the comment insertion logic on account.move."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.AccountMove = cls.env["account.move"]
        cls.Partner = cls.env["res.partner"]
        cls.Journal = cls.env["account.journal"]
        cls.Account = cls.env["account.account"]
        cls.AccountType = cls.env["account.account.type"]

        cls.company = cls.env.company

        # Partner with a specific language to verify the lang in context
        cls.partner = cls.Partner.create(
            {
                "name": "Test Partner",
                "lang": "es_ES",
            }
        )

        # Ensure we have a sale journal
        cls.journal = cls.Journal.search([("type", "=", "sale")], limit=1)
        if not cls.journal:
            journal_vals = {
                "name": "Test Sale Journal",
                "code": "TSA",
                "type": "sale",
            }
            # V18 puede tener company_id o company_ids en journal
            if "company_id" in cls.Journal._fields:
                journal_vals["company_id"] = cls.company.id
            elif "company_ids" in cls.Journal._fields:
                journal_vals["company_ids"] = [(4, cls.company.id)]
            cls.journal = cls.Journal.create(journal_vals)

        # Ensure we have an "income" account for the invoice line
        if "account_type" in cls.Account._fields:
            cls.income_account = cls.Account.search(
                [("account_type", "=", "income")], limit=1
            )
        else:
            cls.income_account = cls.Account.search([], limit=1)

        if not cls.income_account:
            account_vals = {
                "name": "Test Income Account",
                "code": "TINC",
            }
            if "account_type" in cls.Account._fields:
                account_vals["account_type"] = "income"
            elif "user_type_id" in cls.Account._fields:
                acc_type = cls.AccountType.search(
                    [("type", "=", "income")], limit=1
                ) or cls.AccountType.search([], limit=1)
                account_vals["user_type_id"] = acc_type.id

            if "company_id" in cls.Account._fields:
                account_vals["company_id"] = cls.company.id
            elif "company_ids" in cls.Account._fields:
                account_vals["company_ids"] = [(4, cls.company.id)]

            cls.income_account = cls.Account.create(account_vals)

        # Dynamically get the comodel of comment_template_ids
        comment_field = cls.AccountMove._fields.get("comment_template_ids")
        if not comment_field:
            raise AssertionError(
                "The field 'comment_template_ids' must exist on account.move "
                "for this test to run."
            )
        cls.CommentTemplate = cls.env[comment_field.comodel_name]

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

        # Create a basic move for testing (valid accounting-wise)
        cls.move = cls.AccountMove.create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "journal_id": cls.journal.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test line",
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "account_id": cls.income_account.id,
                        },
                    )
                ],
                "comment_template_ids": [
                    (6, 0, [cls.template_top.id, cls.template_bottom.id])
                ],
            }
        )

    def test_action_insert_comments_splits_by_position(self):
        """Templates are split into top_comment and bottom_comment by position."""
        move = self.move

        # We patch render_comment to control the output per template.
        def fake_render_comment(self_move, template):
            if template == self.template_top:
                return "TOP-HTML;"
            if template == self.template_bottom:
                return "BOTTOM-HTML;"
            return ""

        with patch.object(
            type(move), "render_comment", autospec=True, side_effect=fake_render_comment
        ):
            move.action_insert_comments()

        self.assertEqual(
            move.top_comment,
            "TOP-HTML;",
            "Top template should be rendered into top_comment.",
        )
        self.assertEqual(
            move.bottom_comment,
            "BOTTOM-HTML;",
            "Bottom template should be rendered into bottom_comment.",
        )

    def test_action_insert_comments_uses_partner_language(self):
        """render_comment must be called with the partner language in context."""
        move = self.move
        seen_langs = []

        def fake_render_comment(self_move, template):
            # Capture the lang used on the template's context
            seen_langs.append(template._context.get("lang"))
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
