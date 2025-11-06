# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResFileContainerType(models.Model):
    _name = "res.file.containertype"
    _description = "Type of containers"
    _order = "name"

    # Display name
    name = fields.Char(
        required=True,
        index=True,
        help="Short name of the container type (e.g., Box, Folder, Pallet).",
    )

    # Optional longer description
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
