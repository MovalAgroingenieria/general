# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import datetime, timedelta
from unittest.mock import patch

from freezegun import freeze_time
from odoo import fields
from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.tests.common import TransactionCase
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


class TestDST(TransactionCase, CronMixinCase):
    def _check_cron_date_after_run(self, cron, datetime_str):
        datetime_current = datetime.strptime(
            datetime_str, DEFAULT_SERVER_DATETIME_FORMAT
        ) + timedelta(seconds=10)
        datetime_current_str = datetime_current.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        with freeze_time(datetime_current_str):
            cron.write(
                {"nextcall": datetime_str, "daylight_saving_time_resistant": True}
            )
            cron.flush_recordset()
            self.env.flush_all()
            default_progress = {"done": 0, "remaining": 0, "timed_out_counter": 0}
            job = {**cron.read(load=None)[0], **default_progress}
            timezone_date_orig = fields.Datetime.context_timestamp(cron, cron.nextcall)
            zone = getattr(timezone_date_orig.tzinfo, "zone", None) or getattr(
                timezone_date_orig.tzinfo, "key", None
            )
            self.assertEqual(zone, "Europe/Paris")
            day_after_date_orig = (timezone_date_orig + timedelta(days=1)).day
            self.registry.enter_test_mode(self.cr)
            try:

                def patched_run(server_action):
                    server_action.env["ir.cron"]._notify_progress(done=1, remaining=0)

                with patch.object(
                    self.registry["ir.actions.server"],
                    "run",
                    patched_run,
                ):
                    self.registry["ir.cron"]._process_job(
                        self.registry.db_name,
                        self.registry.cursor(),
                        job,
                    )
            finally:
                self.registry.leave_test_mode()
            cron.invalidate_recordset()
            timezone_date_after = fields.Datetime.context_timestamp(cron, cron.nextcall)
            self.assertEqual(day_after_date_orig, timezone_date_after.day)
            self.assertEqual(timezone_date_orig.hour, timezone_date_after.hour)

    def test_cron_dst_europe_paris(self):
        user = self.env.ref("base.user_root")
        user.write({"tz": "Europe/Paris"})
        user.invalidate_recordset()
        cron = self.env["ir.cron"].create(
            {
                **self._get_cron_data(self.env),
                "name": "TestCron DST",
                "code": "model.search([])",
                "interval_number": 1,
                "interval_type": "days",
                "nextcall": fields.Datetime.now() + timedelta(hours=1),
            }
        )
        self._check_cron_date_after_run(cron, "2021-10-30 15:00:00")
        self._check_cron_date_after_run(cron, "2021-03-27 15:00:00")
