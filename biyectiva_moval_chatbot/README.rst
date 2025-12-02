.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1|

===============================
Biyectiva Moval Chatbot module
===============================


**Table of contents**

.. contents::
   :local:

Description
===========

This addon provides dedicated security groups and a materialized view that
exposes mail notifications tied to project tasks for Moval's Biyectiva
chatbot in Odoo 16.

The snapshot aggregates task metadata, reviewers, assignees, and tags so the
chatbot can query a stable dataset without touching the transactional tables.

Use Cases
=========

The materialized view supports the following chatbot use cases using the added timesheet fields:

.. list-table::
   :widths: 15 15 20 15 15 20
   :header-rows: 1

   * - Use Case
     - Category
     - Query Example
     - Expected Output
     - Manual Process (Odoo)
     - Technical Implementation (Chatbot)
   * - **Detection of tasks with timesheets but missing descriptions**
     - Quality of Imputations
     - "Tell me tasks with timesheets but without comments."
     - List + last timesheet + responsible
     - Timesheets > List View > Group by Task > Search lines with empty "Description".
     - Filter ``mail.notification.chatbot``:

       ``timesheet_total_hours > 0`` AND ``timesheet_last_description`` is empty.
   * - **Inverse detection: Messages without timesheets**
     - Real Dedication Control
     - "Tell me tasks with messages but without timesheets."
     - List + last messages + responsible to log hours
     - Open Task with recent activity > "Timesheets" tab > Check for recent lines.
     - Filter ``mail.notification.chatbot``:

       ``timesheet_total_hours = 0`` (or NULL).

Authors
~~~~~~~

* Moval Agroingeniería S.L.

Contributors
~~~~~~~~~~~~

* Guillermo Amante <gamante@moval.es>
* Samuel Fernández Verdú <sfernandez@moval.es>
* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Jesús Martínez <jmartinez@moval.es>
* Miguel Mora <mmora@moval.es>
* Miguel Ángel Rodríguez <marodriguez@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainer
~~~~~~~~~~

This module is maintained by Moval Agroingeniería.

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :alt: Moval Agroingeniería
   :target: https://moval.es