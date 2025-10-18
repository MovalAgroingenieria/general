# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    verifacti_enabled = fields.Boolean(
        string='Send to Verifacti',
        default=False,
        help='Enable automatic sending of invoices to Verifacti for this journal'
    )
