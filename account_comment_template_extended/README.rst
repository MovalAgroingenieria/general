.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1|

===============================
Account Comments Extended
===============================

**Table of contents**

.. contents::
   :local:


Description
===========

This module extends the behavior of comment templates on ``account.move``.

By default, all selected comment templates are inserted directly into the
invoice report. With this module installed, templates are **not** added
automatically. Instead, the user must click the **Insert comments** button.

This action will:

* Render each selected template,
* Split them by their configured position (before or after invoice lines),
* Insert them into two editable HTML fields:
  * **Top Comment**
  * **Bottom Comment**

The rendered comments can then be edited freely in the invoice, without
modifying the original templates.

This provides more control over how comment templates are applied to invoices.


Credits
=======

Authors
~~~~~~~

* Moval Agroingeniería S.L.


Contributors
~~~~~~~~~~~~

* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Jesús Martínez <jmartinez@moval.es>
* Miguel Mora <mmora@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Jorge Vera <jvera@moval.es>


Maintainers
~~~~~~~~~~~

This module is maintained by **Moval Agroingeniería**.

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :alt: Moval Agroingeniería
   :target: https://moval.es
