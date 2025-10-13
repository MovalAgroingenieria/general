.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1|


===============================
Telework by Department Capacity
===============================

**Table of contents**

.. contents::
   :local:


Description
===========

Odoo 16 CE module to declare telework/on-site by employee (full day) and control capacity by department without using hr.leave or calendar.event.

Features
--------

* **Daily declaration**: Employees can declare their work mode (telework/on-site) with Draft/Confirmed states
* **Capacity control**: Flexible or strict system to control capacity by department
* **Configurable rules**: Rules by specific date and weekly patterns to define capacities
* **Default capacity**: Configuration at department and global level
* **Multiple views**: Tree, form, calendar, pivot and graph for complete analysis
* **Notifications**: Automatic notification for overcapacity to department managers
* **Tracking**: Complete tracking system with integrated chatter

Installation
============

1. Copy the module to the addons directory
2. Update the module list
3. Install the `hr_telework_tracking_site_capacity` module

Configuration
=============

Basic configuration
-------------------

1. Go to **Settings > Telework** to configure:

   * **Capacity policy**: Flexible (allows overcapacity with warning) or Strict (blocks overcapacity)
   * **Global default capacity**: Value used when there are no specific rules
   * **Cut-off day & time**: Deadline that triggers the automatic generation of next week's plan
   * **Auto-confirmation day & time**: Moment when the system confirms the automatically generated declarations

Department configuration
------------------------

1. Go to **Employees > Configuration > Departments**
2. Edit each department and configure the **Default capacity (full day)**

Capacity rules
--------------

1. Go to **Telework > Capacities**
2. Create specific rules:

   * **Specific date**: For specific days (holidays, special events)
   * **Weekly pattern**: To define capacities by day of the week

Usage
=====

For employees
-------------

1. Go to **Telework > Declarations**
2. Create new declaration by selecting:

   * Employee (auto-filled if it's the user themselves)
   * Date
   * Mode (Telework/On-site)

3. Confirm the declaration

For managers
------------

* View all declarations from their department
* Receive notifications when capacity is exceeded
* Receive weekly summaries when the automatic planning and confirmation run
* Full access to reports and analysis

Permissions
-----------

* **Basic users**: Can create and modify their own declarations
* **HR Manager**: Full access to all declarations and configuration
* **Telework Manager**: Specific group with management permissions

Credits
=======

Authors
-------

* Moval Agroingeniería S.L.

Contributors
------------

* Guillermo Amante <gamante@moval.es>
* Juan José Bautista <jjbautista@moval.es>
* Samuel Fernández <sfernandez@moval.es>
* Pablo García <pgarcia@moval.es>
* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Jesús Martínez <jmartinez@moval.es>
* José Javier Méndez <jjmendez@moval.es>
* Miguel Mora <mmora@moval.es>
* Miguel Ángel Rodríguez <marodriguez@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainers
-----------

This module is maintained by Moval Agroingeniería.

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :alt: Moval Agroingeniería
   :target: http://moval.es
