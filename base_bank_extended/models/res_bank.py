# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'


    _sql_constraints = [
        ('unique_number', 'Check(1=1)', 'Account Number must be unique (NOT)'),
    ]
