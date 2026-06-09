# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class WebsiteConfigSettings(models.TransientModel):
    _inherit = "website.config.settings"

    @api.model
    def default_get(self, fields_list):
        values = super(WebsiteConfigSettings, self).default_get(fields_list)
        website_id = values.get("website_id")
        if website_id and "website_name" in fields_list:
            website = self.env["website"].browse(website_id)
            company_name = website.company_id.name
            if company_name:
                values["website_name"] = company_name
        return values

    @api.onchange("website_id")
    def _onchange_website_id_set_company_name(self):
        if self.website_id and self.website_id.company_id and self.website_id.company_id.name:
            self.website_name = self.website_id.company_id.name
