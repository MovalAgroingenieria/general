# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class ResFileStage(models.Model):
    _name = 'res.file.stage'
    _description = 'File Stage'
    _order = 'sequence, name'

    name = fields.Char(
        string="Name",
        required=True)

    sequence = fields.Integer(
        string="Sequence",
        default=10)

    fold = fields.Boolean(
        string='Folded in Kanban',
        help='This stage is folded in the kanban view.')

    is_closing_stage = fields.Boolean(
        string='Closing Stage',
        help='Indicates if this stage is a closing stage.')

    file_ids = fields.One2many(
        string='Files',
        comodel_name='res.file',
        inverse_name='stage_id')
