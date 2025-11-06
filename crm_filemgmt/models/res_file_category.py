# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResFileCategory(models.Model):
    _name = "res.file.category"
    _description = "Categories of Files"

    name = fields.Char(
        required=True,
        translate=False,
        index=True,
    )

    is_readonly = fields.Boolean(string="Read-only Category", default=False)

    parent_id = fields.Many2one(
        comodel_name="res.file.category",
        string="Parent Category",
    )

    notes = fields.Html()

    file_ids = fields.One2many(
        comodel_name="res.file",
        inverse_name="category_id",
        string="Associated Files",
    )

    number_of_files = fields.Integer(
        string="Files",
        compute="_compute_number_of_files",
        store=True,
    )

    _sql_constraints = [
        ("unique_name", "UNIQUE (name)", "Existing category name."),
    ]

    def unlink(self):
        for record in self:
            if record.is_readonly:
                # pylint disable=no-raise-unlink
                raise UserError(_("The read only categories cannot be removed."))
        return super().unlink()

    @api.depends("file_ids")
    def _compute_number_of_files(self):
        for record in self:
            record.number_of_files = len(record.file_ids)

    def action_get_files(self):
        self.ensure_one()
        if self.file_ids:
            tree_view = self.env.ref("crm_filemgmt.res_file_view_tree_related").id
            form_view = self.env.ref("crm_filemgmt.res_file_view_form").id
            search_view = self.env.ref("crm_filemgmt.res_file_view_search").id

            return {
                "type": "ir.actions.act_window",
                "name": _("Files"),
                "res_model": "res.file",
                "target": "current",
                "domain": [("id", "in", self.file_ids.ids)],
                "view_mode": "tree,form",
                "views": [(tree_view, "tree"), (form_view, "form")],
                "search_view_id": search_view,
            }
        return False
