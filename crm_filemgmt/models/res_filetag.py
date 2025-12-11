# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResFiletag(models.Model):
    """Model to manage tags for files.

    Tags allow categorizing and filtering files across different stages and workflows.
    Each tag can have a color for visual identification in kanban and list views.
    """
    _name = "res.filetag"
    _description = "File Tags"
    _order = "sequence, name, id"
    _rec_name = "name"

    # ==========================
    # FIELDS DEFINITION
    # ==========================

    name = fields.Char(
        string="Tag Name",
        required=True,
        translate=True,  # Changed to True for multi-language support
        index=True,
        trim=True,
        help="Short, human-readable tag name. Keep it concise for display in badges.",
    )

    color = fields.Integer(
        string="Color",
        default=0,
        help=(
            "Color index used for visual representation: "
            "0: Default, 1: Green, 2: Yellow, 3: Orange, 4: Red, "
            "5: Purple, 6: Blue, 7: Cyan, 8: Light Green, 9: Magenta, "
            "10: Pink, 11: Brown, 12: Navy"
        ),
    )

    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Defines the order of tags in dropdowns and lists. Lower numbers appear first.",
    )

    active = fields.Boolean(
        string="Active",
        default=True,
        help="Uncheck to hide the tag without deleting it.",
    )

    notes = fields.Html(
        string="Description",
        sanitize=True,
        strip_style=False,
        help="Optional detailed description or instructions about when to use this tag.",
    )

    # ==========================
    # RELATIONAL FIELDS
    # ==========================

    file_ids = fields.Many2many(
        string="Files",
        comodel_name="res.file",
        relation="res_file_filetag_rel",
        column1="filetag_id",
        column2="file_id",
        help="Files that have been tagged with this tag.",
    )

    file_count = fields.Integer(
        string="File Count",
        compute="_compute_file_count",
        store=False,
        help="Number of files associated with this tag.",
    )

    # ==========================
    # COMPUTE METHODS
    # ==========================

    @api.depends('file_ids')
    def _compute_file_count(self):
        """Compute the number of files tagged with each tag."""
        for tag in self:
            tag.file_count = len(tag.file_ids)

    # ==========================
    # CONSTRAINTS
    # ==========================

    @api.constrains('name')
    def _check_name_length(self):
        """Ensure tag name is not too long for UI display."""
        for tag in self:
            if len(tag.name) > 50:
                raise ValidationError(_(
                    "Tag name should not exceed 50 characters for proper display."
                ))

    @api.constrains('color')
    def _check_color_range(self):
        """Ensure color index is within a reasonable range."""
        for tag in self:
            if tag.color < 0 or tag.color > 99:  # Odoo typically supports 0-11
                raise ValidationError(_(
                    "Color index must be between 0 and 99."
                ))

    _sql_constraints = [
        (
            "res_filetag_name_unique",
            "unique(name)",
            "A file tag with this name already exists. Tag names must be unique.",
        ),
        (
            "res_filetag_sequence_positive",
            "CHECK(sequence >= 0)",
            "Sequence must be a positive number or zero.",
        ),
    ]

    # ==========================
    # ORM METHODS
    # ==========================

    def copy(self, default=None):
        """Override copy method to handle unique name constraint.

        Appends '(copy)' to duplicated tag names.
        """
        self.ensure_one()
        if default is None:
            default = {}
        if 'name' not in default:
            default['name'] = _("%s (copy)") % self.name
        return super(ResFiletag, self).copy(default)

    def name_get(self):
        """Custom display name showing tag with color indicator.

        Returns: List of tuples (id, display_name)
        """
        result = []
        for tag in self:
            # You could add emoji or other indicators based on color
            name = tag.name
            result.append((tag.id, name))
        return result

    # ==========================
    # BUSINESS LOGIC METHODS
    # ==========================

    def action_view_files(self):
        """Action to view all files with this tag.

        Returns: Action dictionary to open files in list view filtered by tag.
        """
        self.ensure_one()
        return {
            'name': _('Files Tagged "%s"') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'res.file',
            'view_mode': 'list,form,kanban',
            'domain': [('tag_ids', 'in', self.ids)],
            'context': {
                'default_tag_ids': [(4, self.id)],
                'search_default_tag_id': self.id,
            },
            'help': _('''
                <p class="o_view_nocontent_smiling_face">
                    View all files tagged with "%s"
                </p>
            ''') % self.name,
        }

    def get_tag_badge_class(self):
        """Return CSS class for badge styling based on color.

        Useful for custom web views or reports.
        """
        self.ensure_one()
        color_map = {
            0: 'default', 1: 'success', 2: 'warning', 3: 'warning',
            4: 'danger', 5: 'info', 6: 'primary', 7: 'info',
            8: 'success', 9: 'danger', 10: 'danger', 11: 'default', 12: 'primary'
        }
        return color_map.get(self.color, 'default')

    # ==========================
    # SEARCH METHODS
    # ==========================

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced search for tags.

        Searches in both name and notes fields.
        """
        if args is None:
            args = []
        domain = args + ['|', ('name', operator, name), ('notes', operator, name)]
        return self._search(domain, limit=limit, access_rights_uid=name_get_uid)

    # ==========================
    # UI/VIEW HELPERS
    # ==========================

    def get_color_style(self):
        """Return inline CSS style for the color.

        Useful for custom kanban or list views.
        """
        self.ensure_one()
        # This is a simplified example - Odoo has its own color system
        color_map = {
            1: 'background-color: #21b799;',  # Green
            2: 'background-color: #ffc107;',  # Yellow
            3: 'background-color: #fd7e14;',  # Orange
            4: 'background-color: #dc3545;',  # Red
            5: 'background-color: #6f42c1;',  # Purple
            6: 'background-color: #007bff;',  # Blue
            7: 'background-color: #17a2b8;',  # Cyan
            8: 'background-color: #28a745;',  # Light Green
            9: 'background-color: #e83e8c;',  # Magenta
        }
        return color_map.get(self.color, 'background-color: #6c757d;')  # Default grey

    # ==========================
    # STATIC METHODS
    # ==========================

    @api.model
    def get_most_used_tags(self, limit=10):
        """Get the most frequently used tags.

        Args:
            limit (int): Maximum number of tags to return.

        Returns: Recordset of most used tags.
        """
        query = """
            SELECT tag.id, COUNT(file_tag.file_id) as usage_count
            FROM res_filetag tag
            LEFT JOIN res_file_filetag_rel file_tag ON tag.id = file_tag.tag_id
            WHERE tag.active = true
            GROUP BY tag.id
            ORDER BY usage_count DESC, tag.name
            LIMIT %s
        """
        self.env.cr.execute(query, (limit,))
        tag_ids = [row[0] for row in self.env.cr.fetchall()]
        return self.browse(tag_ids)