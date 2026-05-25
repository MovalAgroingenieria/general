.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

======================================
Online Bank Statements: BankInPlay.com
======================================

Description
===========
This module integrates Odoo’s **Online Bank Statements** functionality with **BankInPlay.com**, enabling automated scheduling, retrieval, and processing of bank statement lines through secure callbacks.

Key Features
============
* Registers a webhook in BankInPlay for *close readings* (``lectura_cierre``).
* Automatically creates or updates bank statements upon callback reception.
* Supports two modes of operation — **Same endpoint** (this database receives callbacks) or **Remote endpoint** (callbacks are forwarded to another Odoo instance).
* Journal-level configuration — Date field mapping (Operation Date / Value Date), delay days to adjust date ranges for provider latency, and option to skip empty statements.

Compatibility
=============
* Odoo **18.0**
* Python **3.10+**

Dependencies
============
* Base online provider module (``account_statement_import_online`` or OCA equivalent).
* Python package ``cryptography``.

Installation
============
1. Install required dependencies (including ``cryptography``).
2. Add the module to your *addons path* and update the app list.
3. Install the module from **Apps** in Odoo.
4. Ensure your Odoo base URL is **publicly accessible** if receiving callbacks.

Configuration
=============
System Settings
---------------
Navigate to **Settings → Accounting → Bank & Cash** (or search “BankInPlay”):

* **BankInPlay Integration** — enable.
* **Callback URL** — the public base URL of your Odoo (e.g. ``https://odoo.example.com``).
* **API Key / API Secret** — credentials provided by BankInPlay.
* Click **Register Callbacks** to register the webhook in BankInPlay.

Journal Configuration
---------------------
In your **Bank Journal** → *Online Synchronization*:

* **Service** — ``BankInPlay.com``.
* **API Key / API Secret** — only needed in **Same Endpoint** mode.
* **Endpoint Type** — **Same Endpoint** (this database receives callbacks at ``<base_url>/webhook/bankinplay_callback``) or **Remote Endpoint** (specify the remote Odoo base URL to forward callbacks).
* **BankInPlay Date Field** — choose **Operation Date** or **Value Date**.
* **Delay Days** — adjust for potential provider delays.

How It Works
============
1. A scheduled action (or manual run) requests statement data for a given period.
2. A *close reading* is registered in BankInPlay, returning a ``responseId`` and ``signature``.
3. When BankInPlay sends the callback — in **Same Endpoint** mode the module decrypts and creates/updates the statement; in **Remote Endpoint** mode the decrypted payload is forwarded to the target database.

Security
========
* The callback payload’s ``data`` is encrypted using AES-CBC; it is decrypted using your configured credentials.
* The module temporarily stores routing responses for remote callbacks, which are automatically purged by a scheduled job.
* Use **HTTPS** and protect your endpoints with appropriate proxy or firewall rules.

Scheduled Actions
=================
* **Delete old BankInPlay stored responses**: runs daily to keep temporary data clean.
  You can adjust its frequency from **Settings → Technical → Scheduled Actions**.

Troubleshooting
===============
* **Callbacks not received**
  - Ensure ``<base_url>/webhook/bankinplay_callback`` is publicly reachable.
  - Re-run **Register Callbacks**.
  - Check Odoo logs for POST or timeout errors.

* **“Provider did not return signature/response_id.”**
  - Verify credentials and that the account/IBAN is correctly configured in BankInPlay.

* **“Account not found”**
  - Confirm that the IBAN configured in the journal matches the one in BankInPlay.

* **Decryption errors**
  - Make sure credentials are valid and correspond to the correct BankInPlay environment.

Credits
=======
* Moval Agroingeniería S.L.

Contributors
------------
* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Miguel Mora <mmora@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Jorge Vera <jvera@moval.es>
* César Andrés <candres@moval.es>

Maintainer
----------
.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by **Moval Agroingeniería**.
