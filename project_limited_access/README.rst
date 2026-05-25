.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

======================
Project Limited Access
======================

Description
===========

This module extends the project and project task models by adding restricted access functionality for a specific group of users. The users in this group can view, create, and edit tasks, but are restricted from deleting them. Additionally, tasks inherit a list of restricted users from their parent project, which can be modified, but the restricted users list cannot be changed by members of the restricted access group.

Features:
- New user group with limited permissions for project and task management.
- Tasks inherit restricted users from their parent project.
- Restricted users can view, create, and edit tasks, but cannot delete them.
- Restricted user list is inmutable for this group of users.

Credits
=======

* Moval Agroingeniería S.L.

Contributors
------------

* Samuel Fernández <sfernandez@moval.es>
* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Jesús Martínez <jmartinez@moval.es>
* Miguel Mora <mmora@moval.es>
* Miguel Ángel Rodríguez <marodriguez@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainer
----------

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.
