Security roles
~~~~~~~~~~~~~~

Go to **Settings > Users & Companies > Users** and assign the appropriate role:

* **General Entity / User**: can view all entity and member data (read-only
  access to relationships).
* **General Entity / Manager**: full create, edit, and delete access to all
  entities, members, and relationships.
  Administrators are assigned this role automatically.

Multi-company
~~~~~~~~~~~~~

Relationships (``general.entity.member``) belong to a specific company.
Users will only see relationships that match their currently active companies.
No special configuration is needed — the record rule is installed automatically.
