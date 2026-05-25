.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1|

===========================
External Agent Permissions
===========================

**Table of contents**

.. contents::
   :local:

Description
===========
This module restricts data access for **agent users**: internal users whose
associated contact (``user.partner_id``) is an **agent** in the OCA commission
sense (``res.partner`` with ``agent=True`` from **commission_oca**).

It uses **only permissions**: one security group and record rules. No new
fields are added to contacts, users, or leads. Assignment is done via the
existing OCA field **Agents** (``agent_ids``) on contacts.

Key Features
============
* **Agent users** — Users whose partner has ``agent=True`` get the group
  *Agent user*. Record rules then restrict:

  * **Contacts (res.partner)** — Only the user's own partner and contacts
    that have this agent in **Agents** (``agent_ids``).
  * **Opportunities (crm.lead)** — Only opportunities whose contact has this
    agent in ``agent_ids``.
  * **Sale orders (sale.order)** — Only orders whose partner has this agent
    in ``agent_ids``.
  * **Expenses (hr.expense, hr.expense.sheet)** — Only the user's own
    expenses (where ``employee_id.user_id`` is the current user).

* **Automatic group** — The group *Agent user* is added/removed when:
  the contact's ``agent`` flag is changed, or when a user's contact
  (``partner_id``) is set. On module install, all existing users whose
  partner is already an agent receive the group.

Usage
=====
Installation
~~~~~~~~~~~~
1. Install **commission_oca** (and optionally **hr_expense** if you use
   expense rules).
2. Install this module from Apps.
3. Update the Apps list, search for **External Agent Permissions**, then
   *Install*.

Configuration
~~~~~~~~~~~~~
1. **Define agents** — In **Contacts**, mark the partner as **Creditor/Agent**
   (``agent=True``) and set **Agents** on other contacts where this agent
   is assigned (OCA commission_oca behaviour).

2. **Create the agent user** — Create an internal user linked to that
   partner. The module will automatically add the *Agent user* group when
   the partner has ``agent=True``, so the user will only see contacts,
   opportunities, sale orders, and (if hr_expense is installed) expenses
   associated with that agent.

3. **No extra fields** — Use the standard **Agents** field on contacts to
   assign agents; no wizard or extra assignment UI is required.

Permissions (agent user only)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
+------------------+----------------------------------------------------------+
| Model            | Rule                                                     |
+==================+==========================================================+
| res.partner      | Own partner or contacts with this agent in agent_ids     |
+------------------+----------------------------------------------------------+
| crm.lead         | Opportunities whose partner has this agent in agent_ids  |
+------------------+----------------------------------------------------------+
| sale.order       | Orders whose partner has this agent in agent_ids         |
+------------------+----------------------------------------------------------+
| hr.expense       | Own expenses (employee_id.user_id = user)                 |
+------------------+----------------------------------------------------------+
| hr.expense.sheet | Own expense sheets (same criterion)                      |
+------------------+----------------------------------------------------------+

Compatibility
=============
* Odoo 18.0

Dependencies
~~~~~~~~~~~~
* base
* contacts
* crm
* sales_team
* sale
* commission_oca
* hr_expense (for expense and expense sheet rules)

Credits
=======

Authors
~~~~~~~
* Moval Agroingeniería S.L.

Contributors
~~~~~~~~~~~~
* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Miguel Mora <mmora@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Jorge Vera <jvera@moval.es>
* César Andrés <candres@moval.es>

Maintainers
~~~~~~~~~~~
This module is maintained by Moval Agroingeniería.

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :alt: Moval Agroingeniería
   :target: http://moval.es
