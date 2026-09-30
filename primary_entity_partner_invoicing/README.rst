Primary Entity Partner Invoicing
===============================

This Odoo 18 module preserves the primary entity of a period census on its
invoice lines and allows manual allocation of eligible journal items.
The optional ``account.move.line.primary_entity_id`` field is a stored,
indexed Many2one to ``res.partner``. In Spanish its label is
"Entidad principal".

Installation
------------

Make the compatible 18.0 branches of the ``general`` and ``abs`` repositories,
and their dependencies, available on the Odoo addons path. Install
``primary_entity_partner_invoicing``. Its direct dependencies are
``base_invoicing`` and ``base_general_entity_period_census``.
When replacing version 18.0.1.0.0 in an existing installation, restart Odoo
and upgrade this module (``-u primary_entity_partner_invoicing``) to load the
new views, translations and field behavior.

Behaviour
---------

* On creation, customer/vendor invoice and refund lines resolve the existing
  ``billable_item_model`` / ``billable_item_res_id`` reference in batches.
* Census lines use ``primary_partner_id``. Additional movements first use
  ``primary_partner_id``, then ``census_line_id.primary_partner_id``.
* An explicitly supplied value is preserved, including ``False``. This also
  preserves empty historical values when duplicating or reversing an invoice.
* Source access rights and record rules are respected. Missing or inaccessible
  sources leave the field empty; no elevated access is used.
* Journal items with no census source can be assigned an entity manually.
  Tax lines, receivable/payable lines, payment entries, bank statement entries,
  invoice sections and notes remain read-only. The ORM rejects changes to
  protected lines, including changes through imports or API calls.
* Only product lines of invoices/refunds are enriched automatically. Ordinary
  lines without a supported reference, tax lines, payment terms, sections,
  notes, payment entries and other journal entries are not enriched.
* Copies and reversals retain the original value. Source changes do not update
  invoices, and installation does not backfill existing invoices.
* Deletion of a referenced partner is restricted to preserve traceability.
* Invoice descriptions remain unchanged.

Usage
-----

Enable the optional Primary Entity column on invoice lines, journal items,
or the Invoice Lines list supplied by ``base_invoicing``. The two line search
views support searching by entity, filtering with/without an entity and
grouping by entity. The field is available through standard line exports.
Open a journal item or edit a draft invoice/journal entry to assign an entity
to an eligible line. Invoice lines linked to a census line or additional
movement preserve their automatically assigned historical entity and cannot
be changed manually.

Extension
---------

Override ``account.move.line._get_primary_entity_source_fields()``, call
``super()``, and add a billable model with an ordered tuple of relational
paths ending in a single ``res.partner`` record. The shared creation logic
resolves the first populated path. Ambiguous results are left empty.

Presentation-specific modules can inherit the views and change labels using
the same field, without duplicating the resolution logic.

Tests
-----

Run against a disposable Odoo 18 database with the dependencies available::

    odoo-bin -d test_primary_entity -i primary_entity_partner_invoicing \
        --test-enable --test-tags /primary_entity_partner_invoicing \
        --stop-after-init --without-demo=all

The tests cover customer/vendor invoices, mixed batches, absent references,
excluded line types, historical values, copy/reversal, access restrictions,
source extension, grouping/export, manual allocation and deletion restrictions.
