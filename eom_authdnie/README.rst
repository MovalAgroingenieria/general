.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=========================
DNIe-based Authentication
=========================

Authentication for the frontend based on DNIe.

Description
===========

This module allows DNIe-based authentication to enter to Odoo frontend.

If the DNI of authenticated user is the same as the DNI of an existing partner,
then this partner and the authenticated user will be mapped.

Configuration
=============

1. Copy the *static/php/eoffice_generic.php*, change parameters and filename.

2. Copy or link *static/certs/sede_accepted_certs.pem*.

3. Config your webserver to execute the php and to ask for the certificate.

4. Inherit from main model eom_digitalregister.py and change _cypher_key.

To generate a _cypher_key you can use:

.. code-block::

   openssl rand -base64 24


Accepted certificates
=====================

All accepted certificates, root and subordinate, have been chained into a single
certificate located in *static/certs/sede_accepted_certs.pem*.

This certificate **must be linked or copied** to a place where the
**web server can read it**.

Root certificates
-----------------

+------------+------------------+-----------------------------------------+
| Authority  | Name             | Observations                            |
+============+==================+=========================================+
| FNMT       | AC Raíz FNMT-RCM |                                         |
+------------+------------------+-----------------------------------------+
| ACCV       | ACCVRAIZ1        | CA Raíz (vigente hasta 31/12/2030)      |
+------------+------------------+-----------------------------------------+
| DNIE       | AC RAIZ DNIE 2   | CA Raíz (vigente hasta 27/09/2043)      |
+------------+------------------+-----------------------------------------+
| DGP        | AC DPG RAIZ      |                                         |
+------------+------------------+-----------------------------------------+
| DGP        | DPG RAIZ 2       |                                         |
+------------+------------------+-----------------------------------------+

Intermediate certificates
-------------------------

+------------+------------------------+-----------------------------------------------------------------+
| Authority  | Name                   | Observations                                                    |
+============+========================+=================================================================+
| FNMT       | AC FNMT Usuarios       | CA Subordinada FNMT-RCM para usuarios                           |
+------------+------------------------+-----------------------------------------------------------------+
| FNMT       | AC FNMT Representación | CA Subordinada FNMT-RCM                                         |
+------------+------------------------+-----------------------------------------------------------------+
| FNMT       | AC FNMT Sector Público | CA Subordinada FNMT-RCM para entidadades públicas               |
+------------+------------------------+-----------------------------------------------------------------+
| ACCV       | ACCVCA-120             | CA Subordinada para personas físicas (vigente hasta 31/12/2026) |
+------------+------------------------+-----------------------------------------------------------------+
| ACCV       | ACCVCA-110             | CA Subordinada para entidades (vigente hasta 31/12/2026)        |
+------------+------------------------+-----------------------------------------------------------------+
| DNIE       | AC AC DNIE 001         | CA certificación Subordinada 001                                |
+------------+------------------------+-----------------------------------------------------------------+
| DNIE       | AC AC DNIE 002         | CA certificación Subordinada 002                                |
+------------+------------------------+-----------------------------------------------------------------+
| DNIE       | AC AC DNIE 003         | CA certificación Subordinada 003                                |
+------------+------------------------+-----------------------------------------------------------------+
| DNIE       | AC AC DNIE 004         | CA certificación Subordinada 004                                |
+------------+------------------------+-----------------------------------------------------------------+
| DNIE       | AC AC DNIE 005         | CA certificación Subordinada 005                                |
+------------+------------------------+-----------------------------------------------------------------+
| DNIE       | AC AC DNIE 006         | CA certificación Subordinada 006                                |
+------------+------------------------+-----------------------------------------------------------------+
| DGP        | AC DGP 001             | CA subordinada 001                                              |
+------------+------------------------+-----------------------------------------------------------------+
| DGP        | AC DGP 002             | CA subordinada 002                                              |
+------------+------------------------+-----------------------------------------------------------------+
| DGP        | AC DGP 004             | CA subordinada 004                                              |
+------------+------------------------+-----------------------------------------------------------------+

Downloads
---------

+------------+------------------------------------------------------------------------------------------+--------------+
| Authority  | Link                                                                                     | Observations |
+============+==========================================================================================+==============+
| FNMT       | https://www.sede.fnmt.gob.es/descargas/certificados-raiz-de-la-fnmt                      |              |
+------------+------------------------------------------------------------------------------------------+--------------+
| ACCV       | https://www.accv.es/servicios/ciudadanos-y-autonomos/descarga-de-certificados-jerarquia  |              |
+------------+------------------------------------------------------------------------------------------+--------------+
| DNIE       | https://www.dnielectronico.es/ZIP/ACRAIZ-DNIE2.zip                                       | Raíz         |
+------------+------------------------------------------------------------------------------------------+--------------+
| DNIE       | https://www.dnielectronico.es/PortalDNIe/PRF1_Cons02.action?pag=REF_078                  | Subordinadas |
+------------+------------------------------------------------------------------------------------------+--------------+
| DGP        | https://www.policia.es/_es/certificados_digitales.php                                    |              |
+------------+------------------------------------------------------------------------------------------+--------------+

Credits
=======

* Moval Agroingeniería S.L.

Contributors
------------

* Samuel Fernández Verdú <sfernandez@moval.es>
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

.. image:: https://services.moval.es/static/images/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.
