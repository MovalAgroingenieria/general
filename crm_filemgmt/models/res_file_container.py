# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResFileContainer(models.Model):
    _name = "res.file.container"
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
        string="Location",
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

    # -------------------------
    # Computes
    # -------------------------

    @api.depends("file_ids")
    def _compute_number_of_files(self):
        for rec in self:
            rec.number_of_files = len(rec.file_ids)

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
        """Open the related files in a window action."""
        self.ensure_one()
        if not self.file_ids:
            return False

        tree = self.env.ref(
            "crm_filemgmt.res_file_view_tree_related", raise_if_not_found=False
        )
        form = self.env.ref("crm_filemgmt.res_file_view_form", raise_if_not_found=False)
        search = self.env.ref(
            "crm_filemgmt.res_file_view_search", raise_if_not_found=False
        )

        views = []
        if tree:
            views.append((tree.id, "tree"))
        if form:
            views.append((form.id, "form"))

        return {
            "type": "ir.actions.act_window",
            "name": self.env.context.get("Files", "Files"),
            "res_model": "res.file",
            "views": views or [(False, "tree"), (False, "form")],
            "view_mode": "tree,form",
            "search_view_id": search.id if search else False,
            "target": "current",
            "domain": [("id", "in", self.file_ids.ids)],
            # Optional: preserve container context for downstream logic/filters
            "context": {"default_container_id": self.id},
        }
