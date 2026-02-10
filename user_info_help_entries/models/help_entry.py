# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class HelpEntry(models.Model):
    _name = "user.menu.help.entry"
    _description = "Help entries for user menu"

    name = fields.Char(string="Button Name", required=True)

    url = fields.Char(string="URL", required=True)

    groups = fields.Many2many(
        string="User Groups",
        comodel_name="res.groups",
        relation="help_entry_group_rel",
        column1="help_entry_id",
        column2="group_id",
    )

    active = fields.Boolean(default=True)
