# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=invalid-name

from contextlib import contextmanager
from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TimesheetComplianceCase(TransactionCase):
    @classmethod
    def setUpClass(cls):  # noqa: N805
        super().setUpClass()

        cls._patchers = [
            patch(
                "odoo.addons.mail.models.mail_mail.MailMail.send",
                autospec=True,
                return_value=True,
            ),
            patch(
                "odoo.addons.mail.models.mail_template.MailTemplate.send_mail",
                autospec=True,
                return_value=True,
            ),
        ]
        for p in cls._patchers:
            p.start()

    @classmethod
    def tearDownClass(cls):  # noqa: N805
        for p in cls._patchers:
            p.stop()
        super().tearDownClass()


def cleanup_employee_workday_for_tests(env, employee, day):
    """Remove timesheet, attendance, and compliance rows for one day.

    Use before tests that assume a clean day on long-lived development databases
    (avoids state "fixed" / unique constraint collisions from old runs).
    """
    from odoo import fields

    d = fields.Date.to_date(day)
    aal = env["account.analytic.line"]
    att = env["hr.attendance"]
    # Analytic lines first (data sources), then attendance, then the compliance row.
    domain = [("date", "=", d)]
    if "employee_id" in aal._fields:
        aal.sudo().search(domain + [("employee_id", "=", employee.id)]).unlink()
    elif employee.user_id:
        aal.sudo().search(domain + [("user_id", "=", employee.user_id.id)]).unlink()
    att.sudo().search([("employee_id", "=", employee.id)]).filtered(
        lambda a: a.check_in and fields.Date.to_date(a.check_in) == d
    ).unlink()
    env["timesheet.compliance"].sudo().search(
        [("employee_id", "=", employee.id), ("date", "=", d)]
    ).unlink()


@contextmanager
def skip_compliance_recompute_on(env):
    """Block AAL/attendance hooks that recompute one day so tests can set data first.

    Production hooks call :meth:`recompute_employee_date_pairs` on each line of
    timesheet/attendance; partial data yields warn/issue, then a final balanced
    recompute is promoted to ``fixed`` (reconciled). Tests that need a single
    ``_compute_employee_date``/``compute_for_dates`` on a full day should create
    rows under this context, then run compliance explicitly.
    """
    yield env(context=dict(env.context, skip_timesheet_compliance_recompute=True))
