# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResFileFilelink(models.Model):
    _name = "res.file.filelink"
    _description = "File filelink"

    file_id = fields.Many2one(
        string="File",
        comodel_name="res.file",
        required=True,
        index=True,
        ondelete="cascade",
    )
    related_file_id = fields.Many2one(
        string="Related File",
        comodel_name="res.file",
        required=True,
        ondelete="restrict",
    )
    related_file_subject = fields.Char(
        string="Subject", related="related_file_id.subject"
    )
    related_file_category_id = fields.Many2one(
        string="Category", related="related_file_id.category_id"
    )

    related_file_code = fields.Char(
        string="Related File Code",
        related="related_file_id.alphanum_code",
        store=True,  # Store in database for faster access
        readonly=True,
    )

    _index = [
        ("file_id", "related_file_id"),  # Composite index for common queries
    ]
