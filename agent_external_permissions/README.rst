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
This module extends Odoo's security model to provide **clear and isolated
access control** for **external agents** and **internal salespeople**, with a
strong focus on CRM visibility while preserving standard Sales behavior.

It is designed for **Odoo 18** and relies exclusively on **record rules,
groups, and ACLs**, avoiding fragile view inheritance or hard-coded logic.

Key Features
============
* **External Agents** — Can only access contacts where they are assigned as external agents; Can only access CRM opportunities linked to those contacts; Have **no access** to Sales Orders; External agents assigned to contacts are automatically propagated to opportunities.

* **Internal Salespeople** — Can only access their own CRM opportunities; Are **not restricted** on Sales Orders (standard Odoo behavior applies); Contact visibility is not modified by this module.

* **Automatic Agent Management** — Agents assigned to a contact are automatically propagated to new opportunities; A wizard allows bulk synchronization of agents on existing opportunities.

* **Clean UI Integration** — External agent assignment field added to contacts; Agent visibility added to the opportunity form; Synchronization wizard accessible directly from the contact form.

Usage
=====
Installation
~~~~~~~~~~~~
1. Install the module from Odoo Apps
2. Update the Apps list
3. Search for **External Agent Permissions**
4. Click *Install*

Configuration
~~~~~~~~~~~~~
1. **User Configuration** — Go to *Settings → Users & Companies → Users*; Edit a user and enable **Is External Agent** or **Is Internal Salesperson**; Required group membership is handled automatically.

2. **Contact Configuration** — Open a contact; Assign users in the **External Agents** field; Use the **Update Opportunities Agents** button to propagate changes.

3. **Opportunity Management** — New opportunities inherit agents from the related contact; Existing opportunities can be updated using the wizard; External agents only see opportunities linked to contacts where they are assigned.

Permissions Matrix
~~~~~~~~~~~~~~~~~~
+----------------------+----------------------+------------------------------------+----------------------+
| User Type            | Contacts             | Opportunities                      | Sales Orders         |
+======================+======================+====================================+======================+
| External Agent       | Only assigned        | Opportunities whose contact        | No access            |
|                      | contacts             | has the agent assigned             |                      |
+----------------------+----------------------+------------------------------------+----------------------+
| Internal Salesperson | All contacts         | Only their own opportunities       | All sales orders     |
+----------------------+----------------------+------------------------------------+----------------------+
| Standard User        | All contacts         | Standard Odoo behavior             | Standard behavior    |
+----------------------+----------------------+------------------------------------+----------------------+

Workflow Example
~~~~~~~~~~~~~~~~
1. Create a contact **ABC Corporation**
2. Assign **John** as an External Agent on the contact
3. Create an opportunity linked to **ABC Corporation**
4. The opportunity automatically inherits John as external agent
5. John can see the contact and the opportunity
6. Other external agents cannot see them
7. Internal salespeople only see opportunities assigned to themselves

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

Credits
=======

Authors
~~~~~~~~
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

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :alt: Moval Agroingeniería
   :target: http://moval.es
