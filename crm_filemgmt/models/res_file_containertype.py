# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResFileContainerType(models.Model):
    _name = "res.file.containertype"
    _description = "Type of containers"
    _order = "name"

    # Add image for visual identification
    image = fields.Image(
        string="Type Image",
        max_width=1024,
        max_height=1024,
        help="Image representing this container type",
    )

    # Add icon for UI representation
    icon = fields.Char(
        string="Icon Class",
        help="CSS icon class for this container type (e.g., 'fa fa-box')",
    )

    # Add color for visual distinction
    color = fields.Integer(
        string="Color Index", default=0, help="Color for kanban and list views"
    )

    # Add dimensions or specifications
    dimensions = fields.Char(
        string="Dimensions", help="Physical dimensions (e.g., '30x40x20 cm')"
    )

    # Add capacity reference
    default_capacity = fields.Integer(
        string="Default Capacity",
        default=100,
        help="Default number of files this container type can hold",
    )

    # Add active flag for archiving
    active = fields.Boolean(default=True, help="Uncheck to archive this container type")

    # Track creation and modification
    create_uid = fields.Many2one("res.users", string="Created by", readonly=True)
    create_date = fields.Datetime(string="Created on", readonly=True)
    write_uid = fields.Many2one("res.users", string="Last Updated by", readonly=True)
    write_date = fields.Datetime(string="Last Updated on", readonly=True)

    name = fields.Char(
        required=True,
        index=True,
        help="Short name of the container type (e.g., Box, Folder, Pallet).",
    )

    description = fields.Char(
        help="Optional description for this container type.",
    )

    notes = fields.Html(
        help="Free-form notes related to this container type.",
    )

    _sql_constraints = [
        (
            "container_type_name_uniq",
            "unique(name)",
            "A container type with this name already exists.",
        ),
    ]

    # Add display name computation
    def _compute_display_name(self):
        for record in self:
            if record.description:
                record.display_name = f"{record.name} - {record.description}"
            else:
                record.display_name = record.name
