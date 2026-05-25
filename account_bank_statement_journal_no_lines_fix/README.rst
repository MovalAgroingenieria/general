.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1|


===========================================
Account Bank Statement Journal No Lines Fix
===========================================

**Table of contents**

.. contents::
   :local:


Description
===========
This module fixes issues with the account.bank.statement model by:

* Making the journal field visible and editable in the bank statement form view
* Allowing manual journal selection when creating new bank statements
* Making the date field editable for better control
* Fixing the journal computation to work from the manually selected journal instead of only from statement lines

This ensures that bank statements can be properly created and linked to specific journals even when no statement lines exist yet.


Credits
=======

Authors
~~~~~~~

* Moval Agroingeniería S.L.


Contributors
~~~~~~~~~~~~

* Guillermo Amante <gamante@moval.es>
* Samuel Fernández <sfernandez@moval.es>
* Pablo García <pgarcia@moval.es>
* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Jesús Martínez <jmartinez@moval.es>
* Miguel Mora <mmora@moval.es>
* Miguel Ángel Rodríguez <marodriguez@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainers
~~~~~~~~~~~

This module is maintained by Moval Agroingeniería.

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :alt: Moval Agroingeniería
