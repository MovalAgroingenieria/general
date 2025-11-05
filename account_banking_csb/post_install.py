# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, api


def _coerce_env(*args):
    """v14–v18 compatible hook signature: returns (env, cr)."""
    if len(args) == 1 and isinstance(args[0], api.Environment):
        return args[0], args[0].cr
    if len(args) >= 2:
        cr = args[0]
        return api.Environment(cr, SUPERUSER_ID, {}), cr
    raise TypeError("Invalid hook signature")


def update_bank_journals(*args):
    """
    Odoo 18: attach CSB Direct Debit to all bank journals using
    account.payment.method.line (per-journal lines), not the old M2M.
    """
    env, _cr = _coerce_env(*args)
    Journal = env["account.journal"].sudo()
    PmLine = env["account.payment.method.line"].sudo()

    # Your payment method defined in XML (inbound direct debit)
    method = env.ref("account_banking_csb.csb_direct_debit_payments", raise_if_not_found=False)
    if not method:
        return  # method not installed; nothing to do

    # All bank journals
    journals = Journal.search([("type", "=", "bank")])

    # Create the line only if missing (idempotent)
    for journal in journals:
        exists = PmLine.search_count([
            ("journal_id", "=", journal.id),
            ("payment_method_id", "=", method.id),
            ("payment_type", "=", "inbound"),
        ])
        if not exists:
            PmLine.create({
                "journal_id": journal.id,
                "payment_method_id": method.id,
                "payment_type": "inbound",
            })
