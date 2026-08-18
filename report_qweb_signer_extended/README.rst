.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

================================
Qweb PDF Reports Signer Extended
================================

This module extends report_qweb_signer with a safer behavior for certificate
resolution in report signing.

It adds these adjustments:

* Allows using ``-`` in certificate path/password as an explicit flag to skip
  signing for that certificate record.
* Keeps strict validation for certificate and password files before invoking
  the signer.
* Applies the fix without modifying the original OCA module.

Installation
============

This module depends on:

* report_qweb_signer

Place this addon in your custom addons path and update the apps list.

Usage
=====

* Configure signing certificates in the same way as report_qweb_signer.
* Install this module.
* Print Qweb PDF reports as usual.

If a certificate has path or password file set to ``-``, signing is skipped for
that certificate.

Credits
=======

* Moval Agroingenieria

Maintainer
==========

This module is maintained by Moval Agroingenieria.
