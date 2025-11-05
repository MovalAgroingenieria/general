# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, api


def update_bank_journals(cr, registry):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        ajo = env["account.journal"]
        journals = ajo.search([("type", "=", "bank")])
        sdd = env.ref("account_banking_csb.csb_direct_debit_payments")
        if sdd:
            journals.write({"inbound_payment_method_ids": [(4, sdd.id)]})
    return
