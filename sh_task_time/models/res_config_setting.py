# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    sh_is_default_description = fields.Boolean('Description Auto Filled ?')
    sh_multiple_task = fields.Boolean('Multiple Task Allowed ?')


class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    sh_is_default_description = fields.Boolean(
        'Description Auto Filled ?',
        related='company_id.sh_is_default_description',
        readonly=False)
    sh_multiple_task = fields.Boolean(
        'Multiple Task Allowed ?',
        related='company_id.sh_multiple_task',
        readonly=False)