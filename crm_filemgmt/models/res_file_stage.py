# -*- coding: utf-8 -*-
# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResFileStage(models.Model):
    """Model to manage file stages in a workflow.

    Stages represent different statuses that files can go through in their lifecycle.
    This model supports kanban views with foldable columns and marking closing stages.
    """

    _name = "res.file.stage"
    _description = "File Stage"
    _order = "sequence, name, id"
    _rec_name = "name"

    # ==========================
    # FIELDS DEFINITION
    # ==========================

    name = fields.Char(
        string="Stage Name",
        required=True,
        index=True,
        translate=True,  # Consider adding translation support
        help="Stage label shown on kanban columns and forms.",
    )

    sequence = fields.Integer(
        default=10,
        help="Lower values appear first in lists and as left-most kanban columns. "
        "Stages are ordered by this sequence number.",
    )

    fold = fields.Boolean(
        string="Folded in Kanban",
        default=False,
        help="If enabled, this stage will be folded (collapsed) in kanban view. "
        "Useful for stages that are not frequently used or are final states.",
    )

    is_closing_stage = fields.Boolean(
        default=False,
        help="Mark as closing stage to indicate the file should be considered closed. "
        "Files in this stage can be filtered as completed or archived.",
    )

    active = fields.Boolean(
        default=True,
        help="If unchecked, it will allow you to hide the stage without removing it.",
    )

    # ==========================
    # RELATIONAL FIELDS
    # ==========================

    file_ids = fields.One2many(
        string="Files",
        comodel_name="res.file",
        inverse_name="stage_id",
        help="Files currently in this stage.",
    )

    file_count = fields.Integer(
        string="Number of Files",
        compute="_compute_file_count",
        store=False,
        help="Count of files in this stage.",
    )

    color = fields.Integer(help="Color for kanban views")
    is_starting_stage = fields.Boolean(string="Starting Stage", default=False)
    allowed_group_ids = fields.Many2many("res.groups", string="Allowed Groups")

    # ==========================
    # COMPUTE METHODS
    # ==========================

    @api.depends("file_ids")
    def _compute_file_count(self):
        """Compute the number of files in each stage."""
        for stage in self:
            stage.file_count = len(stage.file_ids)

    _sql_constraints = [
        (
            "res_file_stage_name_unique",
            "unique(name)",
            "A stage with this name already exists. Stage names must be unique.",
        ),
        (
            "res_file_stage_sequence_positive",
            "CHECK(sequence >= 0)",
            "Sequence must be a positive number or zero.",
        ),
    ]

    # ==========================
    # ORM METHODS
    # ==========================

    def copy(self, default=None):
        """Override copy method to handle unique name constraint.

        Append '(copy)' to the name when duplicating a stage.
        """
        self.ensure_one()
        if default is None:
            default = {}
        if "name" not in default:
            default["name"] = self.env._("%s (copy)", self.name)
        return super().copy(default)

    def name_get(self):  # pylint: disable=deprecated-name-get
        """Custom display name for stages.

        Returns: List of tuples (id, display_name)
        """
        result = []
        for stage in self:
            name = stage.name
            if stage.is_closing_stage:
                name = f"{name} ✅"
            result.append((stage.id, name))
        return result

    # ==========================
    # BUSINESS LOGIC METHODS
    # ==========================

    def action_view_files(self):
        """Action to view all files in this stage.

        Returns: Action dictionary to open the files in list view.
        """
        self.ensure_one()
        return {
            "name": self.env._("Files in %s", self.name),
            "type": "ir.actions.act_window",
            "res_model": "res.file",
            "view_mode": "list,form",
            "domain": [("stage_id", "=", self.id)],
            "context": {"default_stage_id": self.id},
        }

    # ==========================
    # UI/VIEW HELPERS
    # ==========================

    def get_stage_color(self):
        """Return a color based on stage properties.

        Useful for kanban views to visually distinguish stages.
        """
        self.ensure_one()
        if self.is_closing_stage:
            return 10  # Green
        if self.fold:
            return 2  # Grey
        return 0  # Default

    @api.model
    def get_default_stage(self):
        """Get the default stage (first by sequence).

        Returns: Recordset of the default stage or empty recordset.
        """
        return self.search([], order="sequence", limit=1)
