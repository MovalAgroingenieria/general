.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1|

==============
Base Assembly
==============

**Base Assembly** is the core Odoo module for **corporate assemblies** (junta general, asamblea): it defines assembly records, agenda items, attendees, vote delegations, representations, quorum settings, and **roll-call / manual voting** flows on top of *base_vote*.

It targets **AF-style** workflows (convocation, attendance, ballots, delegation documents) with QWeb reports and optional mail templates.

Features
========

* **Assembly types** — reusable configuration (vote types, partner domain for convocable members, default quorum).
* **Assemblies** — scheduling (first/second call), location, state (draft → published → in progress → closed), linked agenda and attendees.
* **Agenda** — ordered items with vote modes: no vote, weighted roll-call, manual yes/no/abstention/blank, manual multi-option; optional ballot options; integration hooks for surveys in companion modules.
* **Attendees** — registration, presence/absence, attendance type (on-site/remote), optional TIN checks for confirmation, signatures for attendance documents.
* **Delegations** — delegate vote weight by vote type, with validation rules (no chains, overlap checks).
* **Representations** — agent/represented member links for governance scenarios.
* **Voting** — open roll-call sessions, per-line votes, results; uses *vote.type* and partner votes from *base_vote*.
* **Reports** — attendance (present / all / with delegation), call register, representation forms, voting ballots (including nominative variants where applicable).
* **Portal / HTTP** — optional attendance confirmation and related flows via controllers (see security and deployment notes).

Dependencies
============

* ``base``, ``mail``, ``web``
* ``base_vat`` — VAT/TIN validation when confirming attendees (context can relax checks where needed).
* ``link_tracker`` — tracking on attendance / mail links where configured.
* ``base_vote`` — vote types and partner vote storage (**required**).

Installation
============

#. Install **Base vote** (*base_vote*) first.
#. Install **Base Assembly** from *Apps*.

Security
========

Two main groups:

* **Assembly User** — read-oriented access with **record rules** scoped to the user’s assemblies/attendees/votes.
* **Assembly Manager** — **model ACL** for create/write on assembly objects.

Manager **does not** automatically include User. If a manager must also be constrained by user rules, assign **both** groups. Details: ``security/assembly_security.xml``.

Configuration
=============

* Assign groups to users.
* Define **assembly types** and **vote types** before creating assemblies.
* On assemblies, complete agenda, attendees, and open votings from the documented menus (Assemblies, Agenda items, Called members, Votings, Representations, Configuration).

Extending
=========

Companion addons (same ecosystem) may add operator UI, survey import, or WUA-specific models; this module stays the **data and report core**.

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

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :alt: Moval Agroingeniería
   :target: http://moval.es
