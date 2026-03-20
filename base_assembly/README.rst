.. Copyright 2026 Moval Agroingeniería
.. License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

================
Base Assembly
================

Assembly management: agenda, attendance, delegations and voting.

Features
========

* Assembly types and assemblies with state workflow (draft, announced, open, in session, closed, cancelled)
* Agenda items with optional vote types and votings
* Attendees (present/remote) with vote totals from base_vote and delegations
* Delegations (delegator → delegate) per vote type with convocable-partner checks
* Quorum (percentage or fixed, 1st/2nd call)
* Voting lines (yes/no/abstention/blank) and result aggregation

Usage
=====

#. Create an assembly type and define vote types and default quorum.
#. Create an assembly, set dates and agenda.
#. Use "Generate attendees" to create attendee records from the partner domain.
#. Open registration; partners confirm attendance or delegate votes.
#. Start session; run votings from agenda items and close the assembly.

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
