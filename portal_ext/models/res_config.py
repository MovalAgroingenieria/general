# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class BaseConfigSettings(models.TransientModel):
    _inherit = "base.config.settings"

    partner_child_portal = fields.Boolean(
        string="Partner child portal access",
        config_parameter='portal_ext.partner_child_portal',
        default=False,
        help="If checked, child partners will be granted portal access instead of res.partner."
    )

    @api.multi
    def set_default_values(self):
        values = self.env['ir.values'].sudo()
        values.set_default('base.config.settings', 'partner_child_portal',
                           self.partner_child_portal)