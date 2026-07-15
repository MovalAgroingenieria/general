This module fixes an issue introduced by
``account_invoice_accounting_date_equal_bill_date`` on Odoo 18.0.

That module forces the accounting date of supplier invoices and refunds to be
equal to the bill date (``invoice_date``). When a supplier bill is created
without a bill date yet (for example when dragging a PDF onto the invoice, or
when creating the bill manually before filling the bill date), the accounting
date is left empty, which raises a required-field validation error.

This module inherits ``account.move`` and, for supplier bills whose accounting
date ends up empty, falls back to today's date, restoring the standard Odoo
behaviour while keeping the original module's intent (accounting date equal to
the bill date whenever a bill date is set).
