# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    # @INFO: Annual tax_period no longer includes the issuance ordinal
    #        ("1º AÑO 2026" -> "AÑO 2026"). Recompute stored values.
    env = api.Environment(cr, SUPERUSER_ID, {})
    order_model = env['account.payment.order']
    orders = order_model.search([('periodicity', '=', 'A')])
    env.add_todo(order_model._fields['tax_period'], orders)
    order_model.recompute()
