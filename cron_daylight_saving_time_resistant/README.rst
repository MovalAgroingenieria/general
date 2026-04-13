Cron daylight saving time resistant (Odoo 10)
==============================================

Port of `OCA/server-tools/cron_daylight_saving_time_resistant` (14.0) for Odoo 10.

Adds a boolean *DST resistant* on ``ir.cron`` so that after a daylight-saving
transition the next run keeps the same **local** time of day.

**Tests (optional dev dependencies on Python 2.7):**

* ``freezegun`` (tested with 0.3.15)
* ``python-dateutil`` >= 2.7 — older 2.5.x makes freezegun fail on import
  (``AttributeError: 'module' object has no attribute 'UTC'``).

Example::

  pip install freezegun 'python-dateutil>=2.7'

The unit test calls ``_process_job`` with the same cursor for job and lock
(``job_cr is cron_cr``), which matches how Odoo runs the logic and avoids
``enter_test_mode`` (Odoo 10’s API differs from 14+).

Then::

  odoo-bin ... -u cron_daylight_saving_time_resistant --test-enable --stop-after-init --workers=0
