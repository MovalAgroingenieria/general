.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1|


=====================
Attendances Self Edit
=====================

**Table of contents**

.. contents::
   :local:


Description
===========

This module modifies the behavior of the parent HR Attendance module, allowing
employees to create and edit their own attendances.

All attendance that is changed, by a user (Manual Attendance security group) or
by the administrator (Officer or Administrator security groups), is marked as
Edited.

Any attendance that is changed by the user (Manual Attendance security group)
outside the allowed range (30 minutes before or after the current moment)
requires filling in the Observations field with a comment of more than 6
characters and is marked as Modified.

Both Edited and Modified attendances can be searched and grouped using filters.


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

Maintainers
~~~~~~~~~~~

This module is maintained by Moval Agroingeniería.

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :alt: Moval Agroingeniería
   :target: http://moval.es
