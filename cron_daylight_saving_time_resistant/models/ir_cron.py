# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
from datetime import datetime, timedelta

import pytz
from odoo import api, fields, models
from odoo.addons.base.models.ir_cron import _intervalTypes

_logger = logging.getLogger(__name__)


class IrCron(models.Model):
    _inherit = "ir.cron"

    daylight_saving_time_resistant = fields.Boolean(
        help=(
            "Adjust the next execution time so the job keeps the same local clock "
            "time after daylight saving time starts or ends (typically twice a year)."
        ),
    )

    @api.model
    def _calculate_daylight_offset(self, nextcall, delta, now):
        tz = nextcall.tzinfo
        if not tz:
            return timedelta(0)
        before_offset = tz.normalize(nextcall).utcoffset()
        cursor = nextcall
        while cursor <= now:
            cursor += delta
        after_offset = tz.normalize(cursor).utcoffset()
        return after_offset - before_offset

    def _reschedule_later(self, job):
        resistant = job.get("daylight_saving_time_resistant")
        job_nextcall = job.get("nextcall")
        super()._reschedule_later(job)
        if not resistant:
            return
        cron = self.env["ir.cron"].browse(job["id"]).sudo()
        delta = _intervalTypes[job["interval_type"]](job["interval_number"])
        now = fields.Datetime.context_timestamp(cron, datetime.utcnow())
        nextcall_raw = (
            fields.Datetime.from_string(job_nextcall)
            if isinstance(job_nextcall, str)
            else job_nextcall
        )
        nextcall_orig = fields.Datetime.context_timestamp(cron, nextcall_raw)
        if nextcall_orig >= now:
            return
        diff_offset = cron._calculate_daylight_offset(nextcall_orig, delta, now)
        if not diff_offset:
            return
        self.env.cr.execute(
            "SELECT nextcall FROM ir_cron WHERE id = %s",
            (job["id"],),
        )
        row = self.env.cr.fetchone()
        if not row or not row[0]:
            return
        new_nextcall = fields.Datetime.context_timestamp(cron, row[0])
        new_nextcall -= diff_offset
        self.env.cr.execute(
            "UPDATE ir_cron SET nextcall = %s WHERE id = %s",
            (
                fields.Datetime.to_string(new_nextcall.astimezone(pytz.UTC)),
                job["id"],
            ),
        )
