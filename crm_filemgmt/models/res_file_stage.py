# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResFileStage(models.Model):
    _name = "res.file.stage"
    _description = "File Stage"
    _order = "sequence, name"

    name = fields.Char(
        required=True,
        index=True,
        help="Stage label shown on kanban columns and forms.",
    )

    sequence = fields.Integer(
        default=10,
        help="Lower values appear first in lists and as left-most kanban columns.",
    )

    fold = fields.Boolean(
        string="Folded in Kanban",
        help="If enabled, this stage will be folded (collapsed) in kanban view.",
    )

    is_closing_stage = fields.Boolean(
        string="Closing Stage",
        help="Mark as closing stage to indicate the file should be considered closed.",
    )

    file_ids = fields.One2many(
        string="Files",
        comodel_name="res.file",
        inverse_name="stage_id",
        help="Files currently in this stage.",
    )

    _sql_constraints = [
        (
            "res_file_stage_name_unique",
            "unique(name)",
            "A stage with this name already exists.",
        ),
    ]
