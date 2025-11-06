# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResFiletag(models.Model):
    _name = "res.filetag"
    _description = "Tags for files"
    _order = "name"

    # Translatable display name for the tag
    name = fields.Char(
        string="File Tag",
        required=True,
        translate=False,
        index=True,
        help="Short, human-readable tag name.",
    )

    # Conventional Odoo color index (used by kanban)
    color = fields.Integer(
        string="Color Index",
        default=0,
        help=(
            "0: grey, 1: green, 2: yellow, 3: orange, 4: red, "
            "5: purple, 6: blue, 7: cyan, 8: light-green, 9: magenta"
        ),
    )

    notes = fields.Html()

    _sql_constraints = [
        (
            "res_filetag_name_unique",
            "unique(name)",
            "A file tag with this name already exists.",
        ),
    ]
