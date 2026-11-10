RemoteControl: Batchline v2
==========================

Independent Odoo 10 MDM integration for the Batchline API-key API. The
original ``remotecontrol_batchline`` module is neither required nor modified.
No crons are created or enabled on installation.

Configuration
-------------

Set the remote control Base URL to the deployment root, including its path
prefix if applicable (not the Swagger URL, nor a URL ending in ``/api``).
Set ``connection_params`` to::

    {"api_key": "YOUR_KEY", "timezone": "Europe/Madrid"}

The timezone applies only to timestamps without an offset. Offset-aware
timestamps are converted directly to UTC. Ambiguous/nonexistent local DST
times are recorded as errors rather than assigned a guessed offset.
SSL verification remains enabled; configure it on the remote control.
Credentials are not copied into the procedure result bag or audit files.
Restrict remote-control configuration access to trusted administrators.

Configure existing MDM devices with::

    {"device_id": "ELEMENT_IDENTIFIER", "start_date": "2026-01-01"}

Configure their sensors with::

    {"tag": "EXACT_TAG_NAME", "start_date": "2026-01-01"}

Import elements produces an inventory JSON attachment, as in the original
module; it does not guess MDM sensor types/units or create MDM devices.
Daily Sync processes configured sensors, respecting selected devices.
It resumes at the last reading's local calendar day (inclusive), then falls
back to sensor start date, device start date, or January 1 of the current
year. Reruns upsert existing timestamps. No undocumented paging or maximum
historical window is assumed.

Readings are isolated with savepoints; failed ORM recomputations are cleared.
Normal execution commits every 1000 attempted readings and each final sensor
batch. Previous committed batches cannot be rolled back on later failures.
Test Run/Test Execute suppress these commits, including audit attachments,
so the framework's outer rollback remains effective. Progress is logged and
each sync produces a JSON audit with per-reading and per-sensor errors.
Calculate Computed Sensors is a separate manual procedure, as in the original
module. It respects selected devices when executed with that selection.

Verified API contract and pressure limitation
--------------------------------------------

Contract reviewed: BLCApi v1 OpenAPI 3.0.1, 2026-11-09. Authentication is
``X-API-KEY`` on every request; there is no token login.

* ``GET /api/alta/elementos``: array of ``identificador``, ``descripcion``,
  ``tags``; tags have ``nombre``, ``idItemOPC``, ``unidad``, ``fecha``, ``valor``.
* ``GET /api/alta/elementos/historico``: required query parameters ``inicio``,
  ``fin`` (YYYY-MM-DD), ``elemento``, ``tag``; array of ``fecha``, ``valor``.

Property names are lower camel case, not the old PascalCase payload.
JSON content is requested even when the API advertises text/plain.
Zero is valid; missing/null/boolean/nonfinite values are errors, not zero.

The supplied Swagger contains pressure schemas but NO dedicated pressure
list/history/provisioning endpoints. The corresponding legacy procedures are
included inactive with an explicit unsupported action, not speculative routes.
Do not enable them until Batchline documents the missing contract. Pressure
tags actually published under elements can be configured using ``device_id``
and ``tag`` and use the normal inventory/history workflow. No automatic
conversion of legacy ``hidrante/electronica/canal`` configuration is possible.
Low-network water meters and hydrant/valve-control operations are out of scope.

Validation
----------

No automated tests are included. Functional validation is manual: configure
the deployment URL and API key, run Import elements, configure device and
sensor parameters, then run Daily Sync and inspect the audit attachment.
Use Test Run first to check the workflow without persisting changes.
Live API access and installation require validation in an Odoo database.

Credits
-------

* Moval Agroingeniería <http://www.moval.es>

License: AGPL-3.0 or later.