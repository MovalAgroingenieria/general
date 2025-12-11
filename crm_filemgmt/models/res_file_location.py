# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResFileLocation(models.Model):
    _name = "res.file.location"
    _description = "Locations of Files"
    _order = "name"

    name = fields.Char(required=True, index=True)

    description = fields.Char()

    location_id = fields.Many2one(
        comodel_name="res.file.location",
        ondelete="restrict",
        index=True,
    )

    image = fields.Image(string="Photo / Image")

    container_ids = fields.One2many(
        comodel_name="res.file.container",
        inverse_name="location_id",
    )

    notes = fields.Html()

    number_of_containers = fields.Integer(
        string="Containers",
        store=True,
        compute="_compute_number_of_containers",
    )

    _sql_constraints = [
        ("unique_name", "UNIQUE (name)", "Existing location name."),
    ]

    # -------------------------
    # Computes
    # -------------------------
    @api.depends("container_ids")
    def _compute_number_of_containers(self):
        for rec in self:
            rec.number_of_containers = len(rec.container_ids)

    # -------------------------
    # Actions
    # -------------------------
    def action_get_containers(self):
        """Open related containers in a window action."""
        self.ensure_one()
        if not self.container_ids:
            return False

        tree = self.env.ref(
            "crm_filemgmt.res_file_container_view_tree_related",
            raise_if_not_found=False,
        )
        form = self.env.ref(
            "crm_filemgmt.res_file_container_view_form", raise_if_not_found=False
        )
        search = self.env.ref(
            "crm_filemgmt.res_file_container_view_search", raise_if_not_found=False
        )

        views = []
        if tree:
            views.append((tree.id, "list"))
        if form:
            views.append((form.id, "form"))

        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Containers"),
            "res_model": "res.file.container",
            "views": views or [(False, "list"), (False, "form")],
            "view_mode": "list,form",
            "search_view_id": search.id if search else False,
            "target": "current",
            "domain": [("id", "in", self.container_ids.ids)],
            "context": {"default_location_id": self.id},
        }
