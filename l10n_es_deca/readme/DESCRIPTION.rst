This module provides a generic transport control document (DECA) for Odoo 18.

A DECA record stores the contractual loading party, the effective carrier,
origin, destination, transport date, goods description and weight, vehicle and
trailer plates, special authorizations, driver data and optional goods lines.

Once issued, the document gets a sequence number and a cryptographically random
access token. A QWeb PDF report is generated with the required data and a QR
code that resolves to a public HTTPS URL, allowing inspection without a login.

The module is multi-company and keeps the core generic: no customer-specific
warehouses, VAT numbers or routes are hardcoded.
