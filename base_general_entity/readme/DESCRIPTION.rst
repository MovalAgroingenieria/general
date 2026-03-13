Generic base module for managing **primary entities** (grouping organizations such as
irrigation communities, cooperatives, or consortia) and **secondary members**
(individuals or subgroups that belong to them).

It reuses the standard ``res.partner`` model and adds an intermediate relationship
model (``general.entity.member``) to handle the many-to-many association between
entities and members.

Key capabilities:

* Mark any contact as a *primary entity*, a *secondary member*, or neither
  (mutually exclusive — a contact cannot be both at the same time).
* Manage N:M relationships with local member codes, sequences, notes, and
  archiving support.
* Global shared code (``entity_global_code``) for cross-entity identification.
* Full multi-company support with record rules.
* Bulk wizard to mark/unmark contacts in batch from the contacts list view.
* Designed as a **base module** — downstream client modules inherit from it to
  add domain-specific fields and logic.
