# -*- coding: utf-8 -*-
from odoo import models, fields


class HelpEntry(models.Model):
    _name = 'user.menu.help.entry'
    _description = 'Help entries for user menu'

    name = fields.Char(
        string='Button Name',
        required=True)

    url = fields.Char(
        string='URL',
        required=True)

    groups = fields.Many2many(
        string='User Groups',
        comodel_name='res.groups',
        relation='help_entry_group_rel',
        column1='help_entry_id',
        column2='group_id')

    active = fields.Boolean(
        string='Active',
        default=True)
