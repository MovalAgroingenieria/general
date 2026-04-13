# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
# Requires freezegun and python-dateutil>=2.7 (dateutil.tz.UTC) for tests on Python 2.7.

from datetime import datetime, timedelta

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase

try:
    from freezegun import freeze_time
except ImportError:
    freeze_time = None


class TestDST(TransactionCase):
    """DST behaviour aligned with OCA cron_daylight_saving_time_resistant tests."""

    def _fetch_job_dict(self, cron):
        self.env.cr.execute('SELECT * FROM ir_cron WHERE id = %s', (cron.id,))
        return self.env.cr.dictfetchone()

    def _check_cron_date_after_run(self, cron, datetime_str):
        self.assertTrue(
            freeze_time,
            'freezegun is required for DST tests (pip install freezegun)',
        )
        datetime_current = (
            datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
            + timedelta(seconds=10)
        )
        datetime_current_str = datetime_current.strftime('%Y-%m-%d %H:%M:%S')
        with freeze_time(datetime_current_str):
            cron.write({
                'nextcall': datetime_str,
                'daylight_saving_time_resistant': True,
            })
            cron.invalidate_cache()
            job = self._fetch_job_dict(cron)
            timezone_date_orig = fields.Datetime.context_timestamp(
                cron, fields.Datetime.from_string(job['nextcall']),
            )
            zone = getattr(timezone_date_orig.tzinfo, 'zone', None)
            self.assertEqual(zone, 'Europe/Paris')
            day_after_date_orig = (timezone_date_orig + timedelta(days=1)).day

            def patched_callback(cron_self, model_name, method_name, args, job_id):
                return None

            import odoo.addons.base.ir.ir_cron as base_ir_cron

            cr = self.env.cr
            with patch.object(
                base_ir_cron.ir_cron,
                '_callback',
                new=patched_callback,
            ):
                # Same cursor as job and lock cursor: enough for unit test;
                # avoids enter_test_mode (Odoo 10 API differs from later versions).
                self.env['ir.cron']._process_job(cr, job, cr)

            cron.invalidate_cache()
            cron = self.env['ir.cron'].browse(cron.id)
            timezone_date_after = fields.Datetime.context_timestamp(
                cron, fields.Datetime.from_string(cron.nextcall),
            )
            self.assertEqual(day_after_date_orig, timezone_date_after.day)
            self.assertEqual(timezone_date_orig.hour, timezone_date_after.hour)

    def test_cron_dst_europe_paris(self):
        if not freeze_time:
            self.skipTest('freezegun is not installed')
        user = self.env.ref('base.user_root')
        user.write({'tz': 'Europe/Paris'})
        user.invalidate_cache()
        cron = self.env['ir.cron'].create({
            'name': 'TestCron DST',
            'user_id': user.id,
            'model': 'ir.autovacuum',
            'function': 'power_on',
            'args': '()',
            'interval_number': 1,
            'interval_type': 'days',
            'numbercall': -1,
            'active': True,
            'nextcall': fields.Datetime.to_string(
                datetime.now() + timedelta(hours=1),
            ),
        })
        self._check_cron_date_after_run(cron, '2021-10-30 15:00:00')
        self._check_cron_date_after_run(cron, '2021-03-27 15:00:00')
