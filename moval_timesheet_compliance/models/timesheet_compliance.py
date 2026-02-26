# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
from datetime import timedelta
from urllib.parse import quote

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class TimesheetCompliance(models.Model):
    _name = "timesheet.compliance"
    _description = "Daily Timesheet Compliance"
    _inherit = ["mail.thread"]
    _order = "date desc, employee_id"

    _sql_constraints = [
        (
            "employee_date_uniq",
            "unique(employee_id, date)",
            "There is already a compliance record for this employee and date.",
        ),
    ]

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        required=True,
        index=True,
        ondelete="cascade",
        tracking=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        related="employee_id.user_id",
        store=True,
        index=True,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        related="employee_id.department_id",
        store=True,
        index=True,
    )
    date = fields.Date(
        required=True,
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    telework = fields.Boolean(tracking=True)

    attendance_hours = fields.Float(readonly=True)
    timesheet_hours = fields.Float(readonly=True)
    delta_hours = fields.Float(readonly=True)

    state = fields.Selection(
        selection=[
            ("ok", "OK"),
            ("warn", "Warning"),
            ("issue", "Issue"),
            ("fixed", "Fixed"),
            ("justified", "Justified"),
            ("escalated", "Escalated"),
        ],
        default="ok",
        tracking=True,
    )

    email_sent_at = fields.Datetime(readonly=True)
    b2_manager_sent_at = fields.Datetime(readonly=True)
    escalated_at = fields.Datetime(readonly=True)

    generic_hours = fields.Float(readonly=True)
    generic_pct = fields.Float(readonly=True)
    generic_state = fields.Selection(
        selection=[
            ("ok", "OK"),
            ("warn", "Warning"),
            ("issue", "Issue"),
        ],
        readonly=True,
    )

    def _sanitize_mail_header(self, value):
        if not value:
            return value
        if not isinstance(value, str):
            value = str(value)
        return value.replace("\n", " ").replace("\r", " ").strip()

    # Cron
    # -------------------------------------------------------------------------

    @api.model
    def _cron_compute_compliance(self):
        today = fields.Date.context_today(self.env.user)
        dates = [
            today - timedelta(days=1),
            today - timedelta(days=2),
        ]
        self.compute_for_dates(dates)

    # Public API
    # -------------------------------------------------------------------------

    def compute_for_dates(self, dates):
        employees = self.env["hr.employee"].search(
            [
                ("user_id", "!=", False),
                ("x_timesheet_compliance_excluded", "=", False),
            ]
        )
        for employee in employees:
            for day in dates:
                self._compute_employee_date(employee, day)

    # Core logic
    # -------------------------------------------------------------------------

    def _compute_employee_date(self, employee, day):
        compliance = self.search(
            [
                ("employee_id", "=", employee.id),
                ("date", "=", day),
            ],
            limit=1,
        )
        if not compliance:
            compliance = self.create(
                {
                    "employee_id": employee.id,
                    "date": day,
                }
            )

        values = compliance._compute_values(employee, day)

        compliance.write(values)

        if compliance.state == "justified":
            return

        if compliance.state == "fixed":
            return

        new_state = compliance._evaluate_state(values)

        tolerance_ok = (
            self.env.company.x_delta_tolerance_ok
            if self.env.company.x_delta_tolerance_ok is not None
            else 0.01
        )
        if abs(values.get("delta_hours", 0.0)) <= tolerance_ok and compliance.state in (
            "warn",
            "issue",
            "escalated",
        ):
            new_state = "fixed"

        compliance.state = new_state

    def _compute_values(self, employee, day):
        attendance_hours = self._get_attendance_hours(employee, day)
        timesheet_hours = self._get_timesheet_hours(employee, day)
        telework = self._get_telework(employee, day)

        delta_hours = attendance_hours - timesheet_hours

        generic_hours = self._get_generic_hours(employee, day, timesheet_hours)
        generic_pct = generic_hours / timesheet_hours if timesheet_hours else 0.0
        generic_state = self._evaluate_generic_state(
            employee,
            generic_pct,
            timesheet_hours,
        )

        return {
            "telework": telework,
            "attendance_hours": attendance_hours,
            "timesheet_hours": timesheet_hours,
            "delta_hours": delta_hours,
            "generic_hours": generic_hours,
            "generic_pct": generic_pct,
            "generic_state": generic_state,
        }

    # Evaluation helpers
    # -------------------------------------------------------------------------

    def _evaluate_state(self, values):
        telework = values.get("telework")
        timesheet_hours = values.get("timesheet_hours", 0.0)
        delta_hours = values.get("delta_hours", 0.0)

        if telework and not timesheet_hours:
            return "issue"

        company = self.env.company
        tolerance_ok = (
            company.x_delta_tolerance_ok
            if company.x_delta_tolerance_ok is not None
            else 0.01
        )
        warn_hours = (
            company.x_delta_warn_hours
            if company.x_delta_warn_hours is not None
            else 0.5
        )

        if abs(delta_hours) <= tolerance_ok:
            return "ok"

        if abs(delta_hours) <= warn_hours:
            return "warn"

        return "issue"

    def _evaluate_generic_state(self, employee, pct, total_hours):
        min_hours = self.env.company.x_generic_min_hours or 0.0
        if total_hours < min_hours:
            return "ok"

        department = employee.department_id
        warn_pct = department.x_generic_warn_pct or self.env.company.x_generic_warn_pct
        issue_pct = (
            department.x_generic_issue_pct or self.env.company.x_generic_issue_pct
        )

        issue_ratio = issue_pct or 0.0
        warn_ratio = warn_pct or 0.0

        if issue_ratio and pct >= issue_ratio:
            return "issue"
        if warn_ratio and pct >= warn_ratio:
            return "warn"
        return "ok"

    # Data sources
    # -------------------------------------------------------------------------

    def _get_attendance_hours(self, employee, day):
        start_dt = fields.Datetime.to_datetime(day)
        end_dt = fields.Datetime.to_datetime(day + timedelta(days=1))
        attendances = self.env["hr.attendance"].search(
            [
                ("employee_id", "=", employee.id),
                ("check_in", ">=", start_dt),
                ("check_in", "<", end_dt),
            ]
        )
        return sum(attendances.mapped("worked_hours"))

    def _get_timesheet_hours(self, employee, day):
        domain = [("date", "=", day)]
        aal = self.env["account.analytic.line"]
        if "employee_id" in aal._fields:
            domain.append(("employee_id", "=", employee.id))
        else:
            domain.append(("user_id", "=", employee.user_id.id))
        lines = aal.search(domain)
        return sum(lines.mapped("unit_amount"))

    def _get_generic_hours(self, employee, day, total_hours):
        if not total_hours:
            return 0.0

        generic_projects = self.env.company.x_generic_project_ids
        if not generic_projects:
            return 0.0

        domain = [
            ("date", "=", day),
            ("project_id", "in", generic_projects.ids),
        ]
        aal = self.env["account.analytic.line"]
        if "employee_id" in aal._fields:
            domain.append(("employee_id", "=", employee.id))
        else:
            domain.append(("user_id", "=", employee.user_id.id))
        lines = aal.search(domain)
        return sum(lines.mapped("unit_amount"))

    def _get_telework(self, employee, day):
        if "hr.telework.day" in self.env:
            telework_day_model = self.env["hr.telework.day"].sudo()
            domain = [
                ("employee_id", "=", employee.id),
                ("date", "=", day),
                ("mode", "=", "remote"),
            ]
            if "state" in telework_day_model._fields:
                domain.append(("state", "in", ["draft", "pending_review", "confirmed"]))
            if telework_day_model.search_count(domain):
                return True

        is_telework_day = getattr(employee, "_is_telework_day", None)
        if is_telework_day:
            return bool(is_telework_day(day))

        return False

    # Cron (emails)
    # -------------------------------------------------------------------------

    @api.model
    def _cron_send_b1_employee_daily_emails(self):
        """B1: Send D-1 compliance summary to employees when required."""
        today = fields.Date.context_today(self.env.user)
        target_date = today - timedelta(days=1)

        compliances = self.search(
            [
                ("date", "=", target_date),
                ("employee_id.user_id", "!=", False),
                ("email_sent_at", "=", False),
            ]
        )
        for compliance in compliances:
            if compliance._should_send_b1_employee_email():
                compliance.action_send_b1_employee_email()

    def _should_send_b1_employee_email(self):
        """B1 rule: send if telework=True or state in warn/issue."""
        self.ensure_one()
        if self.employee_id.x_timesheet_compliance_excluded:
            return False
        if self.email_sent_at:
            return False
        if not self.user_id or not self.user_id.email:
            return False
        return bool(self.telework) or self.state in ("warn", "issue")

    def action_send_b1_employee_email(self):
        """B1: Render template + mark as sent (idempotent)."""
        self.ensure_one()
        if not self._should_send_b1_employee_email():
            return False

        template = self.env.ref(
            "moval_timesheet_compliance.mail_template_timesheet_compliance_daily",
            raise_if_not_found=False,
        )
        if not template:
            return False

        ctx = self._get_b1_email_render_context()
        ctx["timesheet_entries_count"] = self._get_timesheet_entries_count()

        email_from = (
            self.env.company.email or self.env.user.email or "no-reply@example.com"
        ).strip()
        email_from = email_from.replace("\n", " ").replace("\r", " ")

        subject = _("Timesheet compliance - %s") % self.date

        template.with_context(**ctx).send_mail(
            self.id,
            force_send=True,
            raise_exception=True,
            email_values={
                "email_from": email_from,
                "subject": subject,
            },
        )

        self.email_sent_at = fields.Datetime.now()
        self.message_post(
            body=self._get_b1_email_sent_message_body(),
            message_type="notification",
            subtype_xmlid="mail.mt_note",
        )
        return True

    def _get_b1_email_sent_message_body(self):
        """Body for chatter when B1 email is sent."""
        self.ensure_one()
        return _(
            "Daily compliance email (B1) sent to employee on %s."
        ) % fields.Datetime.now().strftime("%d/%m/%Y %H:%M")

    def _get_timesheet_entries_count(self):
        self.ensure_one()
        aal = self.env["account.analytic.line"]
        domain = [("date", "=", self.date)]
        if "employee_id" in aal._fields:
            domain.append(("employee_id", "=", self.employee_id.id))
        else:
            domain.append(("user_id", "=", self.user_id.id))
        return aal.search_count(domain)

    def _get_b1_email_render_context(self):
        """Context consumed by the B1 mail template."""
        self.ensure_one()
        company = self.env.company
        dept = self.employee_id.department_id

        min_hours = company.x_generic_min_hours or 0.0
        warn_pct = (dept.x_generic_warn_pct or company.x_generic_warn_pct) or 0.0
        issue_pct = (dept.x_generic_issue_pct or company.x_generic_issue_pct) or 0.0

        project_rows = self._get_project_hours_breakdown()
        for row in project_rows:
            row["hours_fmt"] = self._format_hours_for_mail(row.get("hours", 0))
        task_rows = self._get_top_tasks_breakdown(limit=10)
        for row in task_rows:
            row["hours_fmt"] = self._format_hours_for_mail(row.get("hours", 0))

        g_pct = self.generic_pct
        if g_pct and g_pct <= 1:
            generic_pct_fmt = self._format_hours_for_mail(g_pct * 100.0) + "%"
        else:
            generic_pct_fmt = (self._format_hours_for_mail(g_pct or 0) or "0") + "%"

        return {
            "project_rows": project_rows,
            "task_rows": task_rows,
            "my_timesheets_url": self._get_my_timesheets_action_url(),
            "generic_min_hours": min_hours,
            "generic_warn_pct": warn_pct,
            "generic_issue_pct": issue_pct,
            "attendance_hours_fmt": self._format_hours_for_mail(self.attendance_hours),
            "timesheet_hours_fmt": self._format_hours_for_mail(self.timesheet_hours),
            "delta_hours_fmt": self._format_hours_for_mail(self.delta_hours),
            "generic_hours_fmt": self._format_hours_for_mail(self.generic_hours),
            "generic_pct_fmt": generic_pct_fmt,
        }

    def _format_hours_for_mail(self, value):
        """Format float hours for email (2 decimals, locale-aware decimal separator)."""
        try:
            lang = self.env["res.lang"]._lang_get(
                self.env.user.lang or self.env.context.get("lang") or "en_US"
            )
            decimal_point = getattr(lang, "decimal_point", ".") or "."
        except Exception:
            decimal_point = "."
        s = "%.2f" % (float(value or 0))
        return s.replace(".", decimal_point)

    def _get_my_timesheets_action_url(self):
        self.ensure_one()
        action = self.env.ref(
            "moval_timesheet_compliance.action_moval_my_timesheets_by_date",
            raise_if_not_found=False,
        )
        if not action:
            return False

        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        if not base_url:
            return False

        ctx = {"moval_timesheet_date": fields.Date.to_string(self.date)}
        fragment = (
            "#action=%s&model=account.analytic.line&view_type=list&context=%s"
            % (
                action.id,
                quote(json.dumps(ctx), safe=""),
            )
        )
        return "%s/web%s" % (base_url.rstrip("/"), fragment)

    # Backward-compatible wrappers
    # -------------------------------------------------------------------------

    @api.model
    def _cron_send_employee_emails(self):
        """DEPRECATED: kept for compatibility; use _cron_send_b1_employee_daily_emails."""
        return self._cron_send_b1_employee_daily_emails()

    @api.model
    def _cron_send_daily_employee_emails(self):
        """DEPRECATED: kept for compatibility; use _cron_send_b1_employee_daily_emails."""
        return self._cron_send_b1_employee_daily_emails()

    def _get_project_hours_breakdown(self):
        self.ensure_one()
        aal = self.env["account.analytic.line"]
        domain = [("date", "=", self.date)]
        if "employee_id" in aal._fields:
            domain.append(("employee_id", "=", self.employee_id.id))
        else:
            domain.append(("user_id", "=", self.user_id.id))

        lines = aal.search(domain)
        totals = {}
        for line in lines:
            project = line.project_id
            if not project:
                continue
            totals.setdefault(project, 0.0)
            totals[project] += line.unit_amount

        rows = [
            {"project_name": project.display_name, "hours": hours}
            for project, hours in totals.items()
        ]
        rows.sort(key=lambda r: r["hours"], reverse=True)
        return rows

    def _get_top_tasks_breakdown(self, limit=10):
        self.ensure_one()
        aal = self.env["account.analytic.line"]
        domain = [("date", "=", self.date)]
        if "employee_id" in aal._fields:
            domain.append(("employee_id", "=", self.employee_id.id))
        else:
            domain.append(("user_id", "=", self.user_id.id))

        lines = aal.search(domain)
        totals = {}
        notes = {}

        for line in lines:
            task = getattr(line, "task_id", False)
            if not task:
                continue
            totals.setdefault(task, 0.0)
            totals[task] += line.unit_amount
            if task not in notes and line.name:
                notes[task] = line.name

        rows = [
            {
                "task_name": task.display_name,
                "hours": totals[task],
                "note": notes.get(task, ""),
            }
            for task in totals
        ]
        rows.sort(key=lambda r: r["hours"], reverse=True)
        return rows[:limit]

    @api.model
    def _cron_send_b2_manager_daily_emails(self):
        today = fields.Date.context_today(self.env.user)
        target_date = today - timedelta(days=1)

        incidents = self.search(
            [
                ("date", "=", target_date),
                ("department_id", "!=", False),
                ("state", "in", ["warn", "issue", "escalated"]),
                ("b2_manager_sent_at", "=", False),
                ("employee_id.x_timesheet_compliance_excluded", "=", False),
            ]
        )
        if not incidents:
            return True

        by_dept = {}
        for rec in incidents:
            by_dept.setdefault(rec.department_id.id, self.browse())
            by_dept[rec.department_id.id] |= rec

        for dept_id, recs in by_dept.items():
            dept = recs[0].department_id
            manager_user = dept.manager_id.user_id if dept.manager_id else False
            manager_email = manager_user.email if manager_user else False
            if not manager_email:
                continue

            template = self.env.ref(
                "moval_timesheet_compliance.mail_template_timesheet_compliance_b2_manager",
                raise_if_not_found=False,
            )
            if not template:
                continue

            ctx = {
                "department_name": dept.display_name,
                "target_date": fields.Date.to_string(target_date),
                "incident_rows": recs._get_b2_rows(),
                "department_timesheets_url": recs._get_b2_department_action_url(
                    dept, target_date
                ),
                "email_to_override": self._sanitize_mail_header(manager_email),
            }
            subject = self._sanitize_mail_header(
                _("Timesheet compliance incidents - %s - %s")
                % (dept.display_name, fields.Date.to_string(target_date))
            )
            email_to = self._sanitize_mail_header(manager_email)
            email_from = (
                self.env.company.email or self.env.user.email or "no-reply@example.com"
            ).strip()
            email_from = email_from.replace("\n", " ").replace("\r", " ")

            template.with_context(**ctx).send_mail(
                recs[0].id,
                force_send=True,
                raise_exception=True,
                email_values={
                    "email_from": email_from,
                    "email_to": email_to,
                    "subject": subject,
                },
            )
            recs.write({"b2_manager_sent_at": fields.Datetime.now()})
            for rec in recs:
                rec.message_post(
                    body=_("Included in manager incident email (B2) on %s.")
                    % fields.Datetime.now().strftime("%d/%m/%Y %H:%M"),
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                )

        return True

    def _get_b2_department_action_url(self, department, target_date):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        if not base_url:
            return False

        employees = self.env["hr.employee"].search(
            [("department_id", "=", department.id)]
        )
        date_str = fields.Date.to_string(target_date)

        domain = [("date", "=", date_str)]
        aal = self.env["account.analytic.line"]
        if "employee_id" in aal._fields:
            domain.append(("employee_id", "in", employees.ids))
        else:
            domain.append(("user_id", "in", employees.mapped("user_id").ids))

        domain_str = quote(json.dumps(domain), safe="")
        return f"{base_url.rstrip('/')}/web#model=account.analytic.line&view_type=list&domain={domain_str}"

    def _get_b2_rows(self):
        rows = []
        for rec in self.sorted(lambda r: r.employee_id.name):
            rows.append(
                {
                    "employee_name": rec.employee_id.name,
                    "telework": "Yes" if rec.telework else "No",
                    "attendance_hours": rec.attendance_hours,
                    "timesheet_hours": rec.timesheet_hours,
                    "delta_hours": rec.delta_hours,
                    "attendance_hours_fmt": rec._format_hours_for_mail(
                        rec.attendance_hours
                    ),
                    "timesheet_hours_fmt": rec._format_hours_for_mail(
                        rec.timesheet_hours
                    ),
                    "delta_hours_fmt": rec._format_hours_for_mail(rec.delta_hours),
                    "state": rec.state,
                    "generic_pct": rec.generic_pct,
                    "generic_pct_fmt": rec._format_hours_for_mail(
                        (rec.generic_pct * 100.0)
                        if rec.generic_pct and rec.generic_pct <= 1
                        else (rec.generic_pct or 0)
                    )
                    + "%",
                    "generic_state": rec.generic_state,
                    "detail_url": rec._get_b2_employee_day_url(),
                }
            )
        return rows

    def _get_b2_employee_day_url(self):
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        if not base_url:
            return False

        date_str = fields.Date.to_string(self.date)
        domain = [("date", "=", date_str)]
        aal = self.env["account.analytic.line"]
        if "employee_id" in aal._fields:
            domain.append(("employee_id", "=", self.employee_id.id))
        else:
            domain.append(("user_id", "=", self.user_id.id))

        domain_str = quote(json.dumps(domain), safe="")
        return f"{base_url.rstrip('/')}/web#model=account.analytic.line&view_type=list&domain={domain_str}"

    @api.model
    def _cron_send_b3_escalate_unresolved(self):
        today = fields.Date.context_today(self.env.user)
        limit_date = today - timedelta(days=2)

        to_escalate = self.search(
            [
                ("date", "<=", limit_date),
                ("state", "in", ["warn", "issue"]),
                ("escalated_at", "=", False),
                ("department_id", "!=", False),
                ("employee_id.x_timesheet_compliance_excluded", "=", False),
            ]
        )
        if not to_escalate:
            return True

        template = self.env.ref(
            "moval_timesheet_compliance.mail_template_timesheet_compliance_b3_escalation",
            raise_if_not_found=False,
        )

        for rec in to_escalate:
            rec.write(
                {
                    "state": "escalated",
                    "escalated_at": fields.Datetime.now(),
                }
            )

            dept = rec.department_id
            manager_user = dept.manager_id.user_id if dept.manager_id else False
            manager_email = manager_user.email if manager_user else False
            if template and manager_email:
                ctx = {
                    "email_to_override": self._sanitize_mail_header(manager_email),
                    "detail_url": rec._get_b2_employee_day_url(),
                }

                email_from = (
                    self.env.company.email
                    or self.env.user.email
                    or "no-reply@example.com"
                ).strip()
                email_from = email_from.replace("\n", " ").replace("\r", " ")

                subject = _("Timesheet compliance escalation - %s - %s") % (
                    rec.employee_id.name,
                    rec.date,
                )
                template.with_context(**ctx).send_mail(
                    rec.id,
                    force_send=True,
                    raise_exception=True,
                    email_values={
                        "email_from": email_from,
                        "subject": self._sanitize_mail_header(subject),
                    },
                )

            rec.message_post(
                body=_(
                    "Incident escalated (B3) and notification sent to manager on %s."
                )
                % fields.Datetime.now().strftime("%d/%m/%Y %H:%M"),
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )

        return True

    def action_mark_justified(self):
        self.write({"state": "justified"})

    @api.model
    def action_open_analysis_today(self):
        today = fields.Date.context_today(self)
        return self._get_analysis_action_with_domain([("date", "=", today)])

    @api.model
    def action_open_analysis_yesterday(self):
        today = fields.Date.context_today(self)
        yesterday = today - timedelta(days=1)
        return self._get_analysis_action_with_domain([("date", "=", yesterday)])

    @api.model
    def action_open_analysis_this_week(self):
        today = fields.Date.context_today(self)
        start_week = today - timedelta(days=today.weekday())
        end_week = start_week + timedelta(days=6)
        return self._get_analysis_action_with_domain(
            [("date", ">=", start_week), ("date", "<=", end_week)]
        )

    @api.model
    def action_open_analysis_this_month(self):
        today = fields.Date.context_today(self)
        start_month = today.replace(day=1)
        return self._get_analysis_action_with_domain(
            [("date", ">=", start_month), ("date", "<=", today)]
        )

    def _get_analysis_action_with_domain(self, domain):
        action = self.env.ref(
            "moval_timesheet_compliance.action_moval_timesheet_compliance_pivot",
            raise_if_not_found=False,
        )
        if not action:
            return {}
        result = action.read()[0]
        result["domain"] = domain
        return result

    def action_open_timesheets(self):
        """Open timesheet lines (account.analytic.line) for this employee and date."""
        self.ensure_one()
        aal = self.env["account.analytic.line"]
        domain = [("date", "=", self.date)]
        if "employee_id" in aal._fields:
            domain.append(("employee_id", "=", self.employee_id.id))
        else:
            domain.append(("user_id", "=", self.user_id.id))
        return {
            "type": "ir.actions.act_window",
            "name": "Timesheets - %s - %s" % (self.employee_id.name, self.date),
            "res_model": "account.analytic.line",
            "view_mode": "tree,form",
            "domain": domain,
            "context": {"default_date": self.date},
        }

    def action_open_attendances(self):
        """Open attendance records (hr.attendance) for this employee and date."""
        self.ensure_one()
        start_dt = fields.Datetime.to_datetime(self.date)
        end_dt = fields.Datetime.to_datetime(self.date + timedelta(days=1))
        return {
            "type": "ir.actions.act_window",
            "name": "Attendances - %s - %s" % (self.employee_id.name, self.date),
            "res_model": "hr.attendance",
            "view_mode": "tree,form",
            "domain": [
                ("employee_id", "=", self.employee_id.id),
                ("check_in", ">=", start_dt),
                ("check_in", "<", end_dt),
            ],
            "context": {"default_employee_id": self.employee_id.id},
        }

    @api.model
    def _cron_send_e3_weekly_generic_quality(self):
        today = fields.Date.context_today(self.env.user)
        if fields.Date.to_date(today).weekday() != 0:
            return

        today = fields.Date.context_today(self.env.user)
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)

        depts = self.env["hr.department"].search([("manager_id", "!=", False)])

        template = self.env.ref(
            "moval_timesheet_compliance.mail_template_timesheet_compliance_e3_weekly",
            raise_if_not_found=False,
        )
        if not template:
            return

        for dept in depts:
            manager_user = dept.manager_id.user_id
            if not manager_user or not manager_user.email:
                continue

            recs = self.search(
                [
                    ("department_id", "=", dept.id),
                    ("date", ">=", last_monday),
                    ("date", "<=", last_sunday),
                ]
            )
            if not recs:
                continue

            rows = {}
            for r in recs:
                emp = r.employee_id
                key = emp.id
                rows.setdefault(
                    key,
                    {"employee_name": emp.name, "total": 0.0, "generic": 0.0},
                )
                rows[key]["total"] += r.timesheet_hours or 0.0
                rows[key]["generic"] += r.generic_hours or 0.0

            employee_rows = []
            for _, v in rows.items():
                pct = (v["generic"] / v["total"]) if v["total"] else 0.0
                employee_rows.append(
                    {
                        "employee_name": v["employee_name"],
                        "total_hours": round(v["total"], 2),
                        "generic_hours": round(v["generic"], 2),
                        "generic_pct": round(pct * 100.0, 2),
                    }
                )

            employee_rows.sort(key=lambda x: x["generic_pct"], reverse=True)
            worst_rows = employee_rows[:5]
            best_rows = list(reversed(employee_rows[-5:]))

            ctx = dict(self.env.context)
            ctx.update(
                {
                    "department_name": dept.display_name,
                    "date_from": fields.Date.to_string(last_monday),
                    "date_to": fields.Date.to_string(last_sunday),
                    "employee_rows": employee_rows,
                    "worst_rows": worst_rows,
                    "best_rows": best_rows,
                    "pivot_url": self._get_compliance_pivot_url(
                        dept, last_monday, last_sunday
                    ),
                }
            )
            ctx.update(
                {"email_to_override": self._sanitize_mail_header(manager_user.email)}
            )

            any_rec = recs[0]
            subject = self._sanitize_mail_header(
                _("Timesheet generic allocation - %s - %s to %s")
                % (
                    dept.display_name,
                    fields.Date.to_string(last_monday),
                    fields.Date.to_string(last_sunday),
                )
            )

            email_from = self._sanitize_mail_header(
                self.env.company.email or self.env.user.email or "no-reply@example.com"
            )
            email_to = self._sanitize_mail_header(manager_user.email)

            template.with_context(ctx).send_mail(
                any_rec.id,
                force_send=True,
                raise_exception=True,
                email_values={
                    "email_from": email_from,
                    "email_to": email_to,
                    "subject": subject,
                },
            )

    def _get_compliance_pivot_url(self, dept, date_from, date_to):
        action = self.env.ref(
            "moval_timesheet_compliance.action_moval_timesheet_compliance_manager",
            raise_if_not_found=False,
        )
        if not action:
            return False

        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        if not base_url:
            return False

        ctx = {
            "search_default_groupby_emp": 1,
            "search_default_groupby_date": 0,
        }
        domain = [
            ("department_id", "=", dept.id),
            ("date", ">=", fields.Date.to_string(date_from)),
            ("date", "<=", fields.Date.to_string(date_to)),
        ]
        fragment = (
            "#action=%s&model=timesheet.compliance&view_type=list&context=%s&domain=%s"
            % (
                action.id,
                quote(json.dumps(ctx), safe=""),
                quote(json.dumps(domain), safe=""),
            )
        )
        return "%s/web%s" % (base_url.rstrip("/"), fragment)
