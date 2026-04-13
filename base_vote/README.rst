.. Copyright 2026 Moval Agroingeniería
.. License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

============
Base Vote
============

Vote types with Jinja2 formula and votes per partner.

Features
========

* Vote types: code, result type (integer/decimal), Jinja2 formula with ``partner`` variable
* Partner domain to restrict which partners get votes
* Partner votes: one record per partner per vote type, computed from formula
* Optional cron to recompute all active vote types

Usage
=====

#. Create a vote type (code, result type, formula, partner domain).
#. Use **Recompute votes** on a vote type to compute votes for all partners in the domain.
#. View partner votes from the vote type (Results tab) or from the partner form.
#. From a contact form, **Recompute my votes** updates only vote types whose partner domain includes that contact; stale lines are removed when the domain no longer matches.

Credits
=======

Authors
~~~~~~~~
* Moval Agroingeniería S.L.

Contributors
~~~~~~~~~~~~
* Alberto Hernández <ahernandez@moval.es>
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
