# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResFileCategory(models.Model):
    _name = "res.file.category"
    _description = "Categories of Files"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # Optional: Add ordering for better UI experience
    _order = "name"

    # Optional: Add parent path for hierarchical queries
    parent_path = fields.Char(index=True)

    kanban_state = fields.Selection(
        [
            ("normal", "Normal"),
            ("done", "Done"),
            ("blocked", "Blocked"),
        ],
        string="Kanban State",
        default="normal",
        tracking=True,
    )

    sequence = fields.Integer(default=10)

    # Add level for hierarchical display
    level = fields.Integer(compute="_compute_level", store=True)

    name = fields.Char(
        required=True,
        translate=False,
        index=True,
    )

    is_readonly = fields.Boolean(
        string="Read-only Category",
        default=False,
        help="Read-only categories cannot be deleted",
    )

    parent_id = fields.Many2one(
        comodel_name="res.file.category",
        string="Parent Category",
        ondelete="restrict",  # Optional: prevent deletion of parent with children
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

    # Optional: Add child categories
    child_ids = fields.One2many(
        comodel_name="res.file.category",
        inverse_name="parent_id",
        string="Subcategories",
    )

    # Optional: Add color for kanban views
    color = fields.Integer(string="Color Index", default=0)

    _sql_constraints = [
        ("unique_name", "UNIQUE (name)", "Existing category name."),
    ]

    def unlink(self):
        for record in self:
            if record.is_readonly:
                raise UserError(_("The read only categories cannot be removed."))
            # Optional: Prevent deletion if category has files
            if record.file_ids:
                raise UserError(
                    _(
                        "Cannot delete category '%s' because it has %d files associated. "
                        "Please reassign the files first."
                        % (record.name, len(record.file_ids))
                    )
                )
        return super().unlink()

    @api.depends("parent_id")
    def _compute_level(self):
        for record in self:
            level = 0
            parent = record.parent_id
            while parent:
                level += 1
                parent = parent.parent_id
            record.level = level

    @api.depends("file_ids")
    def _compute_number_of_files(self):
        for record in self:
            record.number_of_files = len(record.file_ids)

    def action_get_files(self):
        self.ensure_one()
        if self.file_ids:
            # Optional: Use XML IDs safely with fallback
            try:
                tree_view = self.env.ref("crm_filemgmt.res_file_view_tree_related").id
                form_view = self.env.ref("crm_filemgmt.res_file_view_form").id
                search_view = self.env.ref("crm_filemgmt.res_file_view_search").id
            except ValueError:
                # Fallback to default views if specific views not found
                tree_view = False
                form_view = False
                search_view = False

            return {
                "type": "ir.actions.act_window",
                "name": _("Files in category: %s") % self.name,
                "res_model": "res.file",
                "target": "current",
                "domain": [("category_id", "=", self.id)],
                "view_mode": "list,form",
                "views": (
                    [(tree_view, "list"), (form_view, "form")]
                    if tree_view and form_view
                    else False
                ),
                "search_view_id": search_view if search_view else False,
                "context": {
                    "default_category_id": self.id,
                    "search_default_category_id": self.id,
                },
            }
        return False
