# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
# Ported from OCA/server-tools 14.0/cron_daylight_saving_time_resistant

import logging
import datetime as dt

import pytz
from odoo import api, fields, models
from odoo.addons.base.ir.ir_cron import _intervalTypes

_logger = logging.getLogger(__name__)


class IrCron(models.Model):
    _inherit = 'ir.cron'

    daylight_saving_time_resistant = fields.Boolean(
        string='DST resistant',
        help=(
            'Adjust the next execution time so the job keeps the same local '
            'clock time after daylight saving time starts or ends (typically '
            'twice a year).'
        ),
    )

    @api.model
    def _calculate_daylight_offset(self, nextcall, delta, numbercall, now):
        """Return UTC offset delta across DST when advancing nextcall to *now*."""
        tz = nextcall.tzinfo
        if not tz:
            return None
        before_offset = tz.normalize(nextcall).utcoffset()
        cursor = nextcall
        while cursor < now and numbercall:
            if numbercall > 0:
                numbercall -= 1
            if numbercall:
                cursor += delta
        after_offset = tz.normalize(cursor).utcoffset()
        return after_offset - before_offset

    @classmethod
    def _process_job(cls, job_cr, job, cron_cr):
        """Run base job, then correct *nextcall* if DST shifted local wall time."""
        super(IrCron, cls)._process_job(job_cr, job, cron_cr)
        if not job.get('daylight_saving_time_resistant'):
            return
        with api.Environment.manage():
            try:
                cron = api.Environment(job_cr, job['user_id'], {})[cls._name]
                now = fields.Datetime.context_timestamp(cron, dt.datetime.now())
                nextcall_raw = job['nextcall']
                nextcall = fields.Datetime.context_timestamp(
                    cron,
                    fields.Datetime.from_string(nextcall_raw)
                    if not isinstance(nextcall_raw, dt.datetime)
                    else nextcall_raw,
                )
                numbercall = job['numbercall']
                delta = _intervalTypes[job['interval_type']](job['interval_number'])
                diff_offset = cron._calculate_daylight_offset(
                    nextcall, delta, numbercall, now
                )
                if not diff_offset:
                    return
                if not (nextcall < now and numbercall):
                    return
                cron_cr.execute(
                    "SELECT nextcall FROM ir_cron WHERE id = %s",
                    (job['id'],),
                )
                res_sql = cron_cr.fetchall()
                if not res_sql or not res_sql[0][0]:
                    return
                new_nextcall = fields.Datetime.context_timestamp(
                    cron,
                    fields.Datetime.from_string(res_sql[0][0]),
                )
                new_nextcall -= diff_offset
                modified_next_call = fields.Datetime.to_string(
                    new_nextcall.astimezone(pytz.UTC)
                )
                cron_cr.execute(
                    "UPDATE ir_cron SET nextcall=%s WHERE id=%s",
                    (modified_next_call, job['id']),
                )
                cron.invalidate_cache()
            finally:
                job_cr.commit()
                cron_cr.commit()
