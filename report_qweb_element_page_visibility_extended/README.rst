.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

============================================
Report Qweb Element Page Visibility Extended
============================================

This module allows you to use more classes in QWEB Report

Usage
=====

To use this module, you need to:

In the QWEB ``ir.ui.views`` used by your report,
you can add an element with css class with any of the classes described above.
For example if you need to improve invoice report header with
invoice's number in every page but first, and sale order report header
with order's name in every page but last, add this code to external_layout_header::

    <t t-if="o._table=='account_invoice'">
        <div class="not-first-page">
            <span t-esc="o.number"/>
        </div>
    </t>
    <t t-if="o._table=='sale_order'">
        <div class="not-last-page">
            <span t-esc="o.name"/>
        </div>
    </t>

 Credits
 =======

 * Moval Agroingeniería S.L.

 Contributors
 ------------

 * Alberto Hernández <ahernandez@moval.es>
 * Eduardo Iniesta <einiesta@moval.es>
 * Miguel Mora <mmora@moval.es>
 * Juanu Sandoval <jsandoval@moval.es>
 * Salvador sánchez <ssanchez@moval.es>
 * Jorge Vera <jvera@moval.es>

 Maintainer
 ----------

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.
