# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class WuaConfiguration(models.TransientModel):
    _inherit = 'res.config.settings'
    _description = 'Configuration of Moval TLDV API'

    api_key = fields.Char(
        string='API Key',
        config_parameter='project_portal_wiki_tldv.api_key',
    )

    tldv_url = fields.Char(
        string='Tldv URL',
        config_parameter='project_portal_wiki_tldv.tldv_url',
    )

    tldv_default_category_id = fields.Many2one(
        string='Default Category',
        config_parameter='project_portal_wiki_tldv.tldv_default_category_id',
        comodel_name='document.page',
        domain="[('type', '=', 'category')]",
    )

    tldv_default_project_id = fields.Many2one(
        string='Default Project',
        config_parameter='project_portal_wiki_tldv.tldv_default_project_id',
        comodel_name='project.project',
    )

    tldv_default_start_date = fields.Char(
        string='Default Start Date',
        config_parameter='project_portal_wiki_tldv.tldv_default_start_date',
    )
