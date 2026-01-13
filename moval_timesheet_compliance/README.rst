.. image:: https://img.shields.io/badge/license-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

Timesheet Compliance (Daily)
============================

This module provides a **daily timesheet compliance control** per employee,
combining attendance, timesheets, telework information and allocation quality
into a single daily record.

The objective is to offer HR and managers a **clear daily traffic-light view**
of whether working time has been correctly reported, allocated and followed up.


Overview
--------

For each employee and each day, the module evaluates:

* Attendance hours
* Timesheet hours
* Difference between attendance and timesheets
* Telework status
* Quality of time allocation to generic (catch-all) projects

All this information is stored in a single daily compliance record that can be
reviewed, filtered, audited and used for automated notifications.


Compliance Model
----------------

The main model is ``timesheet.compliance``.

Each record represents **one employee on one specific date** and includes:

Employee context
~~~~~~~~~~~~~~~~

* Employee
* Related user
* Department
* Date

Work context
~~~~~~~~~~~~

* Telework (boolean)

Time control
~~~~~~~~~~~~

* Attendance hours
* Timesheet hours
* Delta hours (attendance − timesheets)
* Compliance state:

  * ``ok`` – no deviation detected
  * ``warn`` – small deviation
  * ``issue`` – relevant deviation or missing data
  * ``fixed`` – issue corrected afterwards
  * ``justified`` – manually justified
  * ``escalated`` – escalated to management

Notification tracking
~~~~~~~~~~~~~~~~~~~~~

* Email sent timestamp (employee)
* Manager email sent timestamp
* Escalation timestamp

Allocation quality
~~~~~~~~~~~~~~~~~~

* Generic hours
* Generic percentage
* Generic state (``ok``, ``warn``, ``issue``)


Uniqueness Constraint
---------------------

A SQL-level uniqueness constraint ensures:

* Only one compliance record exists per **employee and date**

This guarantees consistent daily tracking and prevents duplicates.


Generic Project Configuration
-----------------------------

Generic (or catch-all) projects are configured at company level.

These projects are used to evaluate allocation quality and detect excessive
usage of non-specific timesheet entries.

The following parameters can be configured:

* Minimum timesheet hours required to evaluate quality
* Warning percentage
* Issue percentage

Departments may optionally override company thresholds.


Telework Detection
------------------

Telework is evaluated per employee and day.

The computation:

* Uses the telework module if available
* Does **not** infer telework from timesheet lines
* Falls back to explicit telework helpers when required

Telework is stored on the compliance record and used for notification rules.


Daily Computation
-----------------

A scheduled cron job computes compliance automatically.

* Runs once per day (recommended at **06:30**)
* Computes **yesterday (D-1)** and optionally **the day before (D-2)**
* Creates missing records or updates existing ones
* Preserves manual states (``justified`` and ``fixed``)

The computation updates:

* Attendance hours
* Timesheet hours
* Delta hours
* Telework flag
* Generic allocation metrics


Automated Notifications
-----------------------

B1. Daily employee email
~~~~~~~~~~~~~~~~~~~~~~~~

Each employee may receive a daily compliance summary email for the previous day.

Content:

* Date
* Telework status
* Attendance / timesheet / delta / state
* Hours by project
* Top tasks (up to 10)
* Generic allocation block (hours, %, thresholds, state)
* Direct link to *My timesheets for this day*

Sending rules:

* Email is sent if:

  * ``telework = True`` **or**
  * ``state`` is ``warn`` or ``issue``

* Idempotent: sent only once per day per record

B2. Daily manager email by department
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Managers receive one email per department and day, only when incidents exist.

Content:

* Department and date
* One row per employee with ``warn`` / ``issue`` / ``escalated``:

  * Telework
  * Attendance / timesheet / delta
  * Compliance state
  * Generic percentage and state
  * Link to filtered timesheets for that employee and day

Rules:

* No incidents → no email
* One email per department/day
* Idempotent: never sent twice

B3. Automatic escalation after 48h
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unresolved incidents are escalated automatically.

Criteria:

* Record is at least 2 days old
* State is ``warn`` or ``issue``
* Not ``fixed`` nor ``justified``
* Not already escalated

Actions:

* State is set to ``escalated``
* Escalation timestamp is stored
* Notification is sent to management

Each record is escalated only once.


Links and UX
------------

My timesheets for this day
~~~~~~~~~~~~~~~~~~~~~~~~~~

A dedicated action allows users to open their timesheets with filters applied.

* Model: ``account.analytic.line``
* Domain:

  * Date = selected day
  * User = current user

This action is used from email links and respects access rights.

Compliance views for managers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Managers have access to a panel for audit and follow-up.

Available views:

* List view for daily monitoring
* Form view for detailed inspection and manual actions

Search and filters:

* Date
* Department
* Employee
* Telework
* Compliance state
* Generic allocation state

Manual justification and fixing can be applied from the form view.


Security
--------

Access is controlled via dedicated groups:

* Timesheet Compliance Manager

  * Full access to all compliance records

* Timesheet Compliance User

  * Read-only access to compliance records according to record rules

Record rules enforce data isolation accordingly.


Testing
-------

The module includes automated tests covering:

* Daily compliance computation
* Generic project configuration impact
* Telework detection
* Cron execution
* Email notification rules (B1, B2)
* Escalation logic (B3)
* Idempotency and state protection


Credits
-------

* Moval Agroingeniería S.L.


Contributors
------------

* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Miguel Mora <mmora@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Jorge Vera <jvera@moval.es>
* César Andrés Sánchez <csanchez@moval.es>


Maintainer
----------

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :target: https://www.moval.es
   :alt: Moval Agroingeniería

This module is maintained by **Moval Agroingeniería S.L.**
