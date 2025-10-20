# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    verifacti_enabled = fields.Boolean(
        string='Send to Verifactu',
        default=False,
        help='Enable automatic sending of invoices to Verifacti for this journal',
    )