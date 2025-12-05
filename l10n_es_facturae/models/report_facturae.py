# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class ReportFacturae(models.AbstractModel):
    _name = 'report.l10n_es_facturae.template_facturae'

    @api.model
    def render_html(self, docids, data=None):
        invoices = self.env['account.invoice'].browse(docids)
        for invoice in invoices:
            invoice._validate_facturae_data()
        report_obj = self.env['report']
        docargs = {
            'doc_ids': docids,
            'doc_model': 'account.invoice',
            'docs': invoices,
            'data': data,
        }
        return report_obj.render('l10n_es_facturae.template_facturae', docargs)
