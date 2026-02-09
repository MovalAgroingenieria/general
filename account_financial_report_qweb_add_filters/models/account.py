# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountAccount(models.Model):
    """Add group_by for trial balance report (Odoo 18: type is on account.account)."""

    _inherit = "account.account"

    group_by = fields.Selection(
        selection=[
            ("partner_id", "Partner"),
            ("product_id", "Product"),
            ("journal_id", "Journal"),
            ("tag", "Tag"),
            ("analytic_account_id", "Analytic Account"),
            ("/", "Nothing"),
        ],
        string="Balance Lines Grouped By",
        required=True,
        default="/",
        help="Set the field for the account lines to group the lines in "
        "the new balance report.",
    )


# class AccountAccount(models.Model):
#     _inherit = "account.account"
#
#     account_group_01_id = fields.Many2one(
#         string="Level 1 Account Group",
#         comodel_name='account.account.group',
#         index=True,
#         store=True,
#         compute="_compute_account_group_id_01")

# @api.depends('group_id', 'group_id.parent_id')
# def _compute_account_group_id_01(self):
#     for record in self:
#         level = self.group_id.level
#         group = self.group_id
#         while (level != 1):
#             level = self.group_id.parent_id.level
#             group = group.parent_id.group_id
#         record.account_group_01_id = group

# def _compute_account_group_id_01(self):
#     for record in self:
#         # Encuentra el grupo de nivel 1 correspondiente a la cuenta
#         # actual
#         group_nivel_1 = self.env['account.group'].search([
#             ('id', 'parent_of', record.group_id.id),
#             ('level', '=', 1)
#         ], limit=1)
#         record.account_group_01_id = group_nivel_1


class AccountAccountGroup(models.Model):
    _inherit = "account.group"

    account_group_01_id = fields.Char(
        string="Level 1 Account Group",
        index=True,
        compute="_compute_account_group_id_01",
    )

    def _compute_account_group_id_01(self):
        for record in self:
            # Root group (level 1): walk up parent_id until no parent
            group = record
            while group.parent_id:
                group = group.parent_id
            record.account_group_01_id = group.code_prefix_start or ""
