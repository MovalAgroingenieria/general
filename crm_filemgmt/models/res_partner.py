# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from lxml import etree
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError


class ResPartner(models.Model):
    """Extend res.partner with file management capabilities.

    This module adds:
    - File links to partner records
    - Attachment counting and management
    - File-related actions and views
    """
    _inherit = "res.partner"

    # ==========================
    # FIELDS DEFINITION
    # ==========================

    file_ids = fields.One2many(
        string="Linked Files",
        comodel_name="res.file.partnerlink",
        inverse_name="partner_id",
        help="Files that are explicitly linked to this partner through the file management system.",
    )

    number_of_files = fields.Integer(
        string="Number of Files",
        compute="_compute_number_of_files",
        store=False,
        help="Count of files linked through the file management system.",
    )

    attachment_count = fields.Integer(
        string="Total Attachments",
        compute="_compute_attachment_count",
        store=False,
        help="Count of all attachments (including those not in file management system).",
    )

    linked_attachment_count = fields.Integer(
        string="Linked Attachments",
        compute="_compute_linked_attachment_count",
        store=False,
        help="Count of attachments that are part of the file management system.",
    )

    # ==========================
    # COMPUTE METHODS
    # ==========================

    @api.depends('file_ids')
    def _compute_number_of_files(self):
        """Compute the number of files linked through res.file.partnerlink."""
        for partner in self:
            partner.number_of_files = len(partner.file_ids)

    @api.depends_context('uid')
    @api.model
    def _compute_attachment_count(self):
        """Compute the total number of attachments for each partner.

        Uses read_group for performance with large datasets.
        Respects access rights by not using sudo() unless necessary.
        """
        attachment_obj = self.env['ir.attachment']

        if not self.ids:
            for partner in self:
                partner.attachment_count = 0
            return

        # Try to compute with user's access rights first
        try:
            data = attachment_obj.read_group(
                domain=[
                    ('res_model', '=', 'res.partner'),
                    ('res_id', 'in', self.ids),
                    ('type', '!=', 'url'),  # Exclude URL attachments
                ],
                fields=['res_id'],
                groupby=['res_id'],
                lazy=False,
            )
            counts = {d['res_id'][0]: d['__count'] for d in data}
        except AccessError:
            # If user doesn't have access to attachments, use sudo
            data = attachment_obj.sudo().read_group(
                domain=[
                    ('res_model', '=', 'res.partner'),
                    ('res_id', 'in', self.ids),
                    ('type', '!=', 'url'),
                ],
                fields=['res_id'],
                groupby=['res_id'],
                lazy=False,
            )
            counts = {d['res_id'][0]: d['__count'] for d in data}

        for partner in self:
            partner.attachment_count = counts.get(partner.id, 0)


    # ==========================
    # ACTION METHODS
    # ==========================

    def action_open_partner_files(self):
        """Open the partner's attachments in a multi-view window.

        Returns: Action dictionary for opening attachments
        """
        self.ensure_one()
        return {
            "name": _("Partner Attachments"),
            "type": "ir.actions.act_window",
            "res_model": "ir.attachment",
            "view_mode": "kanban,list,form",
            "views": [
                (self.env.ref('base.view_attachment_kanban').id, 'kanban'),
                (self.env.ref('base.view_attachment_tree').id, 'list'),
                (False, 'form'),
            ],
            "domain": [
                ("res_model", "=", "res.partner"),
                ("res_id", "=", self.id),
                ("type", "!=", "url"),
            ],
            "context": {
                "default_res_model": "res.partner",
                "default_res_id": self.id,
                "search_default_my_attachments": 0,
                "create": False,  # Prevent creation from this view
            },
            "target": "current",
        }

    def action_get_files(self):
        """Open partner's file links in a specialized list view."""
        self.ensure_one()

        # Check if user has access to file management using Odoo 18's check_access()
        try:
            self.env['res.file.partnerlink'].check_access('read')
        except AccessError:
            # Convert AccessError to UserError for better user experience
            raise UserError(_(
                "You don't have permission to access the file management system. "
                "Please contact your administrator."
            ))

        if not self.file_ids:
            # Return False to maintain backward compatibility
            return False

        return {
            "type": "ir.actions.act_window",
            "name": _("Linked Files - %s") % self.name,
            "res_model": "res.file.partnerlink",
            "view_mode": "list,form",
            # Use ID-based domain as the test expects
            "domain": [("id", "in", self.file_ids.ids)],
            "context": {
                "default_partner_id": self.id,
                "search_default_partner_id": self.id,
            },
            "target": "current",
        }

    def action_open_file_management(self):
        """Smart action that opens either file links or attachments based on context.

        Returns: Appropriate action based on available data and user permissions
        """
        self.ensure_one()

        # Check if we should show file links or direct attachments
        if self.file_ids and self.env.user.has_group('crm_filemgmt.group_filemgmt_user'):
            return self.action_get_files()
        else:
            return self.action_open_partner_files()

    # ==========================
    # VIEW CUSTOMIZATION METHODS
    # ==========================

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        """Customize the view based on user permissions and context.

        Overrides the base method to:
        - Hide/show file-related buttons based on permissions
        - Add/remove fields based on user groups
        - Modify view structure dynamically
        """
        res = super().get_view(view_id=view_id, view_type=view_type, **options)

        if view_type != 'form':
            return res

        doc = etree.XML(res['arch'])

        # Check if user has access to file management
        has_filemgmt_access = self.env.user.has_group('crm_filemgmt.group_filemgmt_user')

        # Process file-related buttons
        for node in doc.xpath("//button[@name='action_get_files']"):
            if not has_filemgmt_access:
                # Hide button if no access
                modifiers = node.get('modifiers', '{}')
                modifiers_dict = eval(modifiers) if modifiers else {}
                modifiers_dict['invisible'] = True
                node.set('modifiers', str(modifiers_dict))

        # Add smart file button if not present
        if has_filemgmt_access and not doc.xpath("//button[@name='action_open_file_management']"):
            # Find a good place to insert the button (typically in header or sheet)
            header = doc.xpath("//header")[0] if doc.xpath("//header") else None
            if header:
                smart_button = etree.Element('button',
                                             name='action_open_file_management',
                                             type='object',
                                             string='Files',
                                             class_='btn-primary',
                                             context="{'default_partner_id': active_id}",
                                             modifiers=str({'invisible': [('number_of_files', '=', 0)]})
                                             )
                header.insert(0, smart_button)

        # Update the arch with modifications
        res['arch'] = etree.tostring(doc, encoding='unicode')

        return res

    # ==========================
    # BUSINESS LOGIC METHODS
    # ==========================

    def get_file_statistics(self):
        """Get detailed statistics about partner's files.

        Returns: Dictionary with file statistics
        """
        self.ensure_one()

        stats = {
            'total_files': self.number_of_files,
            'total_attachments': self.attachment_count,
            'linked_attachments': self.linked_attachment_count,
            'by_type': {},
            'by_stage': {},
        }

        # Count files by type and stage
        if self.file_ids:
            # Group by file type
            for file_link in self.file_ids:
                file_type = file_link.file_id.type_id.name if file_link.file_id.type_id else 'Unknown'
                stats['by_type'][file_type] = stats['by_type'].get(file_type, 0) + 1

                # Group by stage
                stage = file_link.file_id.stage_id.name if file_link.file_id.stage_id else 'Unknown'
                stats['by_stage'][stage] = stats['by_stage'].get(stage, 0) + 1

        return stats

    def copy(self, default=None):
        """Override copy to handle file relationships.

        By default, don't copy file links when duplicating a partner.
        """
        if default is None:
            default = {}
        default['file_ids'] = False  # Don't copy file links
        return super(ResPartner, self).copy(default)

    # ==========================
    # SEARCH/UTILITY METHODS
    # ==========================

    @api.model
    def search_partners_with_files(self, file_type=None, stage=None):
        """Search for partners with specific file criteria.

        Args:
            file_type (str): Filter by file type name
            stage (str): Filter by file stage name

        Returns: Recordset of matching partners
        """
        domain = []

        if file_type:
            domain.append(('file_ids.file_id.type_id.name', 'ilike', file_type))

        if stage:
            domain.append(('file_ids.file_id.stage_id.name', 'ilike', stage))

        return self.search(domain)

    def get_recent_files(self, limit=5):
        """Get recent files for this partner.

        Args:
            limit (int): Maximum number of files to return

        Returns: Recordset of recent file links
        """
        self.ensure_one()
        return self.file_ids.sorted(key='create_date', reverse=True)[:limit]