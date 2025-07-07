# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class Project(models.Model):
    _inherit = 'project.project'

    komodo_private_folder_urls = fields.Text(
        string='Komodo Private Folder URLs',
    )

    def write(self, vals):
        res = super().write(vals)
        if 'mail_follower_ids' in vals:
            for project in self:
                if project.privacy_visibility == 'portal':
                    project.document_page_ids.write({
                        'mail_follower_ids': [
                            (6, 0, project.mail_follower_ids.ids)]
                    })
        return res
