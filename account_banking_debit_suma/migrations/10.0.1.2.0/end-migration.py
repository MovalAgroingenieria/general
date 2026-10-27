# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    # @INFO: tax_period is first computed in init_models, before the module
    #        translations are loaded, so existing orders would store the
    #        English label. Recompute it once translations are available.
    env = api.Environment(cr, SUPERUSER_ID, {})
    order_model = env['account.payment.order']
    orders = order_model.search([])
    env.add_todo(order_model._fields['tax_period'], orders)
    order_model.recompute()
