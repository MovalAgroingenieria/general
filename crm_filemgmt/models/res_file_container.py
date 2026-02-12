# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResFileContainer(models.Model):
    _name = "res.file.container"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Container of Files"
    _order = "name"

    name = fields.Char(
        required=True,
        index=True,
    )

    description = fields.Char(
        required=True,
        index=True,
    )

    location_id = fields.Many2one(
        comodel_name="res.file.location",
        required=True,
        index=True,
        ondelete="restrict",
    )

    image = fields.Image(string="Photo / Image")

    file_ids = fields.One2many(
        string="Files",
        comodel_name="res.file",
        inverse_name="container_id",
    )

    number_of_files = fields.Integer(
        string="Number of Files",
        store=True,
        compute="_compute_number_of_files",
    )

    containertype_id = fields.Many2one(
        string="Type",
        comodel_name="res.file.containertype",
        index=True,
        ondelete="restrict",
    )

    notes = fields.Html()

    barcode = fields.Char(
        help="Scan barcode to quickly identify container",
        copy=False,
    )

    qr_code = fields.Binary(
        attachment=True, help="QR code for container identification"
    )

    capacity = fields.Integer(
        help="Maximum number of files this container can hold",
        default=100,
    )

    usage_percentage = fields.Float(
        string="Usage %",
        compute="_compute_usage_percentage",
        store=True,
        digits=(5, 2),
    )

    status = fields.Selection(
        [
            ("empty", "Empty"),
            ("low", "Low (< 25%)"),
            ("medium", "Medium (25-75%)"),
            ("high", "High (> 75%)"),
            ("full", "Full"),
        ],
        compute="_compute_status",
        store=True,
    )

    # -------------------------
    # Computes
    # -------------------------

    @api.depends("file_ids")
    def _compute_number_of_files(self):
        for rec in self:
            rec.number_of_files = len(rec.file_ids)

    @api.depends("number_of_files", "capacity")
    def _compute_usage_percentage(self):
        for container in self:
            if container.capacity > 0:
                container.usage_percentage = (
                    container.number_of_files / container.capacity
                ) * 100
            else:
                container.usage_percentage = 0.0

    @api.depends("usage_percentage")
    def _compute_status(self):
        for container in self:
            if container.number_of_files == 0:
                container.status = "empty"
            elif container.usage_percentage < 25:
                container.status = "low"
            elif container.usage_percentage <= 75:
                container.status = "medium"
            elif container.usage_percentage < 100:
                container.status = "high"
            else:
                container.status = "full"

    @api.depends("name", "description", "location_id", "containertype_id")
    def _compute_display_name(self):
        """Display name as: '<description> [<name>]' and optionally
        include location/type."""
        show_extra = bool(self.env.context.get("show_container_data"))
        for rec in self:
            desc = rec.description or ""
            nm = rec.name or ""
            label = f"{desc} [{nm}]"
            if show_extra:
                if rec.location_id:
                    label += (
                        f" {rec.env.context.get('location: ', '')}"
                        f"{rec.location_id.description or ''}]"
                    )
                if rec.containertype_id:
                    label += (
                        f" {rec.env.context.get('type: ', '')}"
                        f"{rec.containertype_id.name or ''}]"
                    )
            rec.display_name = label

    # -------------------------
    # Actions
    # -------------------------
    def action_get_files(self):
        """Open the related files in a window action.

        Returns:
            dict: Window action if container has files
            False: If container has no files (for backward compatibility)
        """
        self.ensure_one()

        # Check if container has files - return False if empty (for test compatibility)
        if not self.file_ids:
            return False

        # Get view references
        tree = self.env.ref(
            "crm_filemgmt.res_file_view_tree_related", raise_if_not_found=False
        )
        form = self.env.ref("crm_filemgmt.res_file_view_form", raise_if_not_found=False)
        search = self.env.ref(
            "crm_filemgmt.res_file_view_search", raise_if_not_found=False
        )

        views = []
        if tree:
            views.append((tree.id, "list"))
        if form:
            views.append((form.id, "form"))

        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Files in Container: %s", self.name),
            "res_model": "res.file",
            "views": views or [(False, "list"), (False, "form")],
            "view_mode": "list,form",
            "search_view_id": search.id if search else False,
            "target": "current",
            "domain": [("container_id", "=", self.id)],
            "context": {
                "default_container_id": self.id,
                "search_default_container_id": self.id,
            },
        }
