.. Copyright 2026 Moval Agroingeniería
.. License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

==============
Base Assembly
==============

Base module for assembly management: assembly types, scheduling, agenda,
attendees, vote delegation, quorum, and voting (uses *base_vote*).

**Dependencies:** ``base``, ``base_vote``, ``web``.

**Security:** *Assembly User* is read-oriented with scoped record rules; *Assembly Manager* has model ACL for CRUD. Manager does **not** imply User (see ``security/assembly_security.xml``)—assign both only if you need user rules on a manager login.

Installation
============

Install from Apps after *base_vote* is installed.

Credits
=======

Authors
~~~~~~~

* Moval Agroingeniería

Maintainers
~~~~~~~~~~~

This module is part of the `Moval/moval_addons <https://github.com/Moval/moval_addons/tree/18.0/base_general_entity_period_census>`_ project on GitHub.

You are welcome to contribute.
