# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class Project(models.Model):
    _inherit = 'project.project'

    komodo_private_folder_urls = fields.Text(
        string='Komodo Private Folder URLs',
    )
