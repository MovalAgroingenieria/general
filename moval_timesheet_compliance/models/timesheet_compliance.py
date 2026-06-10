# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=protected-access,translation-not-lazy

import ast
import json
import logging
from datetime import timedelta
from urllib.parse import quote

from odoo import _, api, fields, models

# Core model: one row per (employee, day) with delta, telework, generic Q.
# Cron, mail (B1/B2/B3/E3), and recompute hooks are implemented in this file.

_logger = logging.getLogger(__name__)

B1_DAILY_LOG_PREFIX = "[B1]"
SUPERVISOR_NOTIFICATION_EMAILS = (
    "fmartinez@moval.es",
    "mguerrero@moval.es",
)


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
    b1_last_log_at = fields.Datetime(
        string="B1 last log (timestamp)",
        readonly=True,
        help="Timestamp of the last B1 email attempt or status update.",
    )
    b1_last_log = fields.Text(
        string="B1 last log",
        readonly=True,
        help="Last B1 result for operators (outcome, short reason, recipient, in English).",
    )
    b2_manager_sent_at = fields.Datetime(readonly=True)
    escalated_at = fields.Datetime(readonly=True)
    incident_open_since = fields.Datetime(
        string="Incident open since",
        readonly=True,
        help=(
            "Set when the record first enters Warning or Issue; used for 48h "
            "(B3) automatic escalation. Cleared on OK or Justified."
        ),
    )
    resolved_at = fields.Datetime(
        string="Resolved at",
        readonly=True,
        tracking=True,
        help=(
            "Set when an open incident returns to OK after being in Warning, "
            "Issue, or Escalated."
        ),
    )
    resolved_from_state = fields.Selection(
        selection=[
            ("warn", "Warning"),
            ("issue", "Issue"),
            ("escalated", "Escalated"),
        ],
        string="Resolved from",
        readonly=True,
    )

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

    def _moval_collect_supervisor_emails(self, manager_email=False):
        """Compose deduplicated recipient list for supervisor notifications."""
        raw = []
        if manager_email:
            raw.append(manager_email)
        raw.extend(SUPERVISOR_NOTIFICATION_EMAILS)
        out = []
        seen = set()
        for email in raw:
            clean = self._sanitize_mail_header(email)
            if not clean:
                continue
            key = clean.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(clean)
        return out

    def _moval_supervisor_email_to(self, manager_email=False):
        return ",".join(self._moval_collect_supervisor_emails(manager_email))

    @api.model
    def _moval_build_webclient_url(self, hash_params):
        """Assemble a /web# URL from ordered (key, value) pairs (Odoo 16 webclient)."""
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        if not base:
            return False
        parts = []
        for key, value in hash_params:
            if value in (None, False, ""):
                continue
            parts.append("%s=%s" % (key, quote(str(value), safe="")))
        if not parts:
            return False
        return "%s/web#%s" % (base.rstrip("/"), "&".join(parts))

    @api.model
    def _moval_build_window_action_url(
        self,
        action_xmlid,
        res_model,
        view_type,
        domain,
        company=None,
        res_id=None,
        context=None,
    ):
        """/web# with cids, window action, model, view, optional id/domain/context."""
        action = self.env.ref(action_xmlid, raise_if_not_found=False)
        if not action:
            return False
        company = company or self.env.company
        params = [
            ("cids", str(company.id) if company else "1"),
            ("action", str(action.id)),
            ("model", res_model),
            ("view_type", view_type),
        ]
        if res_id is not None:
            params.append(("id", str(res_id)))
        if domain is not None:
            params.append(("domain", json.dumps(domain, separators=(",", ":"))))
        if context is not None:
            params.append(("context", json.dumps(context, separators=(",", ":"))))
        return self._moval_build_webclient_url(params)

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

    @api.model
    def _cron_timer_watchdog(self):
        """Scheduled action: scan active timers and open incidents."""
        return self.env["timesheet.timer.watchdog"].cron_watchdog_timers()

    # Public API
    # -------------------------------------------------------------------------

    def compute_for_dates(self, dates):
        """Compute compliances; iterates all companies."""
        companies = self.env["res.company"].search([])
        for company in companies:
            self._compute_for_dates_for_company(company, dates)

    @api.model
    def _compute_for_dates_for_company(self, company, dates):
        """Compute for employees belonging to a single company."""
        employees = self.env["hr.employee"].search(
            self._compliance_employee_domain(company)
        )
        for employee in employees:
            for day in dates:
                self.with_company(company).sudo()._compute_employee_date(employee, day)

    @api.model
    def _compliance_employee_domain(self, company):
        """Employees included in the daily compliance batch for one company."""
        return [
            ("user_id", "!=", False),
            ("x_timesheet_compliance_excluded", "=", False),
            "|",
            ("company_id", "=", False),
            ("company_id", "child_of", company.id),
        ]

    # Recompute on timesheet/attendance changes
    # -------------------------------------------------------------------------
    @api.model
    def _compliance_date_for_attendance_checkin(self, check_in, employee):
        """Calendar date matching :meth:`_get_attendance_hours` bucketing of check_in."""
        if not check_in or not employee:
            return False
        ci = fields.Datetime.to_datetime(check_in)
        if not ci:
            return False
        base = fields.Date.to_date(ci)
        for delta in (-1, 0, 1):
            d = base + timedelta(days=delta)
            start = fields.Datetime.to_datetime(d)
            end = fields.Datetime.to_datetime(d + timedelta(days=1))
            if start <= ci < end:
                return d
        return base

    @api.model
    def recompute_employee_date_pairs(self, pairs):
        """Recompute daily compliance for unique (employee_id, date) pairs.

        Safe entry point for hooks: one :meth:`_compute_employee_date` per pair, keeping
        justified handling. Context skip_timesheet_compliance_recompute
        disables. Excluded employees (no user or excluded flag) are skipped.
        """
        if not pairs or self.env.context.get("skip_timesheet_compliance_recompute"):
            return
        for emp_id, the_date in sorted(
            pairs, key=lambda t: (t[0], t[1].isoformat() if t[1] else "")
        ):
            employee = self.env["hr.employee"].browse(emp_id)
            if not employee.exists() or not the_date:
                continue
            if employee.x_timesheet_compliance_excluded or not employee.user_id:
                continue
            company = employee.company_id or self.env.company
            self.with_company(company).sudo()._compute_employee_date(employee, the_date)

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

        new_state = compliance._evaluate_state(values)

        if compliance.state == "escalated" and new_state in ("warn", "issue"):
            new_state = "escalated"

        state_before = compliance.state
        extra = compliance._state_transition_values(state_before, new_state)
        wvals = {"state": new_state}
        if extra:
            wvals.update(extra)
        compliance.write(wvals)

    def _state_transition_values(self, state_before, new_state):
        """Return transition-side values for incident and resolution audit fields."""
        self.ensure_one()
        vals = {}

        if new_state in ("warn", "issue"):
            if not self.incident_open_since or state_before not in ("warn", "issue"):
                vals["incident_open_since"] = fields.Datetime.now()
            vals.update(
                {
                    "resolved_at": False,
                    "resolved_from_state": False,
                }
            )
        elif new_state == "escalated":
            vals.update(
                {
                    "resolved_at": False,
                    "resolved_from_state": False,
                }
            )
        elif new_state == "ok":
            vals["incident_open_since"] = False
            if state_before in ("warn", "issue", "escalated"):
                vals.update(
                    {
                        "resolved_at": fields.Datetime.now(),
                        "resolved_from_state": state_before,
                    }
                )
        elif new_state == "justified":
            vals["incident_open_since"] = False
        elif new_state == "fixed":
            vals["incident_open_since"] = False

        return vals

    def write(self, vals):
        """Keep `incident_open_since` aligned when the state changes."""
        if self.env.context.get("skip_compliance_incident_open_since_sync"):
            return super().write(vals)
        if "state" in vals and "incident_open_since" not in vals:
            n = vals.get("state")
            for rec in self:
                o = rec.state
                ex = rec._state_transition_values(o, n) if o != n else {}
                w = {**vals, **ex} if ex else dict(vals)
                super(TimesheetCompliance, rec).write(w)
            return True
        return super().write(vals)

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
    # Compliance total hours and generic quality use
    # `company_id.x_compliance_excluded_project_ids` (see res.company) so internal
    # absence- or leave-like projects do not distort delta, generic %, or mail tables.
    # Generic projects that are also compliance-excluded do not contribute to
    # `generic_hours` (exclusion takes precedence for quality metrics).
    # -------------------------------------------------------------------------

    @api.model
    def _compliance_excluded_aal_domain_part(self, company):
        """Appendable domain: keep analytic lines on non-excluded projects (or no project)."""
        comp = company or self.env.company
        excl = (
            comp.sudo().with_context(active_test=False).x_compliance_excluded_project_ids.ids
        )
        if not excl:
            return []
        return ["|", ("project_id", "=", False), ("project_id", "not in", excl)]

    @api.model
    def _generic_project_ids_for_compliance(self, company):
        """Generic projects whose hours still count toward generic (quality) metrics."""
        comp = company or self.env.company
        comp_with_archived = comp.sudo().with_context(active_test=False)
        generic = comp_with_archived.x_generic_project_ids
        if not generic:
            return self.env["project.project"].browse([])
        excl = comp_with_archived.x_compliance_excluded_project_ids
        return generic - excl

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
        domain += self._compliance_excluded_aal_domain_part(self.env.company)
        lines = aal.search(domain)
        return sum(lines.mapped("unit_amount"))

    def _get_generic_hours(self, employee, day, total_hours):
        if not total_hours:
            return 0.0

        generic_projects = self._generic_project_ids_for_compliance(self.env.company)
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
    def _b1_employee_cron_domain(self, target_date):
        """Narrow B1 search: D-1, eligible, not sent, not excluded, user with email."""
        return [
            ("date", "=", target_date),
            ("email_sent_at", "=", False),
            ("employee_id.x_timesheet_compliance_excluded", "=", False),
            ("user_id", "!=", False),
            ("user_id.email", "!=", False),
            "|",
            ("telework", "=", True),
            ("state", "in", ("warn", "issue")),
        ]

    @api.model
    def _b1_debug_cron_info(self, target_date=None):
        """Read-only: who the B1 cron would process (for support, safe to call in shell)."""
        if target_date is None:
            today = fields.Date.context_today(self.env.user)
            target_date = today - timedelta(days=1)
        compliances = self.search(self._b1_employee_cron_domain(target_date))
        return {
            "target_date": str(target_date),
            "count": len(compliances),
            "ids": compliances.ids,
        }

    @api.model
    def _cron_send_b1_employee_daily_emails(self):
        """B1: Send D-1 compliance summary to employees when required."""
        today = fields.Date.context_today(self.env.user)
        target_date = today - timedelta(days=1)
        compliances = self.search(self._b1_employee_cron_domain(target_date))
        if not compliances:
            _logger.info(
                "%s cron: no records for date=%s", B1_DAILY_LOG_PREFIX, target_date
            )
            return True
        _logger.info(
            "%s cron: %s record(s) for date=%s",
            B1_DAILY_LOG_PREFIX,
            len(compliances),
            target_date,
        )
        for compliance in compliances:
            comp = compliance.company_id or self.env.company
            with self.env.cr.savepoint(flush=True):
                try:
                    res = (
                        compliance.with_company(comp)
                        .sudo()
                        .action_send_b1_employee_email()
                    )
                    _logger.debug(
                        "%s id=%s action_send_b1_employee_email -> %s",
                        B1_DAILY_LOG_PREFIX,
                        compliance.id,
                        res,
                    )
                except Exception:  # pylint: disable=broad-except
                    _logger.exception(
                        "%s id=%s failed in cron send",
                        B1_DAILY_LOG_PREFIX,
                        compliance.id,
                    )
        return True

    def _b1_employee_recipient_email(self):
        self.ensure_one()
        if not self.user_id or not (self.user_id.email or "").strip():
            return False
        return self._sanitize_mail_header((self.user_id.email or "").strip())

    def _b1_employee_log(self, message):
        self.ensure_one()
        text = f"{B1_DAILY_LOG_PREFIX} {message}".strip()
        return self.sudo().write(
            {
                "b1_last_log_at": fields.Datetime.now(),
                "b1_last_log": text,
            }
        )

    def _b1_employee_chatter(self, body):
        self.ensure_one()
        self.sudo().message_post(
            body=body,
            message_type="notification",
            subtype_xmlid="mail.mt_note",
        )

    def _should_send_b1_employee_email(self):
        """B1: send if telework or warn/issue, not excluded, and not sent yet."""
        self.ensure_one()
        if self.employee_id.x_timesheet_compliance_excluded:
            return False
        if self.email_sent_at:
            return False
        if not self._b1_employee_recipient_email():
            return False
        return bool(self.telework) or self.state in ("warn", "issue")

    def action_send_b1_employee_email(self):
        """B1: queue mail, set sent flag, technical log, and chatter (idempotent)."""
        self.ensure_one()
        me = self.sudo().browse(self.id)
        if me.email_sent_at:
            return False
        if not me._should_send_b1_employee_email():
            me._b1_employee_log(
                "Skipped: not eligible (excluded, no recipient email, or business rules)."
            )
            return False
        if self.sudo().browse(self.id).email_sent_at:
            me._b1_employee_log("Skipped: already sent (concurrent).")
            return False

        template = self.env.ref(
            "moval_timesheet_compliance.mail_template_timesheet_compliance_daily",
            raise_if_not_found=False,
        )
        if not template:
            me._b1_employee_log("Failed: mail template missing (B1).")
            me._b1_employee_chatter(
                "B1: mail template is missing. No email was sent. "
                "Check module data or contact an administrator."
            )
            return False

        ctx = me._get_b1_email_render_context()
        ctx["timesheet_entries_count"] = me._get_timesheet_entries_count()
        recipient = me._b1_employee_recipient_email()
        if not recipient:
            me._b1_employee_log("Failed: no recipient address on user account.")
            me._b1_employee_chatter(
                "B1: not sent: the employee user account has no email address."
            )
            return False

        email_from = (
            (me.company_id or self.env.company).email
            or self.env.user.email
            or "no-reply@example.com"
        )
        email_from = email_from.replace("\n", " ").replace("\r", " ").strip()
        subject = f"Timesheet compliance - {me.date}"

        try:
            comp = me.company_id or self.env.company
            template.with_context(**ctx).with_company(comp).send_mail(
                me.id,
                force_send=True,
                raise_exception=True,
                email_values={
                    "email_from": email_from,
                    "email_to": recipient,
                    "subject": subject,
                },
            )
        except Exception as err:  # pylint: disable=broad-except
            me._b1_employee_log(f"Failed: mail send error ({err}).")
            me._b1_employee_chatter(
                f"B1: sending failed: {err}. The compliance record was not marked as sent."
            )
            _logger.exception("%s id=%s send_mail", B1_DAILY_LOG_PREFIX, me.id)
            return False

        me.write({"email_sent_at": fields.Datetime.now()})
        me._b1_employee_log(f"Sent to {recipient}.")
        me._b1_employee_chatter(
            _("Daily compliance email (B1) sent to %(email)s.") % {"email": recipient}
        )
        return True

    def _get_timesheet_entries_count(self):
        self.ensure_one()
        aal = self.env["account.analytic.line"]
        domain = [("date", "=", self.date)]
        if "employee_id" in aal._fields:
            domain.append(("employee_id", "=", self.employee_id.id))
        else:
            domain.append(("user_id", "=", self.user_id.id))
        domain += self._compliance_excluded_aal_domain_part(
            self.company_id or self.env.company
        )
        return aal.search_count(domain)

    def _get_b1_email_render_context(self):
        """Context consumed by the B1 mail template."""
        self.ensure_one()
        company = self.company_id
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

        result = {
            "project_rows": project_rows,
            "task_rows": task_rows,
            "my_timesheets_url": self._get_my_timesheets_action_url(),
            "compliance_form_url": self._get_compliance_record_form_url(),
            "generic_min_hours": min_hours,
            "generic_warn_pct": warn_pct,
            "generic_issue_pct": issue_pct,
            "attendance_hours_fmt": self._format_hours_for_mail(self.attendance_hours),
            "timesheet_hours_fmt": self._format_hours_for_mail(self.timesheet_hours),
            "delta_hours_fmt": self._format_hours_for_mail(self.delta_hours),
            "generic_hours_fmt": self._format_hours_for_mail(self.generic_hours),
            "generic_pct_fmt": generic_pct_fmt,
        }
        rcp = self._b1_employee_recipient_email()
        if rcp:
            result["email_to_override"] = rcp
        return result

    def _format_hours_for_mail(self, value, lang_code=None):
        """Format float hours for email (2 decimals, locale-aware decimal separator)."""
        try:
            lang = self.env["res.lang"]._lang_get(
                lang_code
                or (self.employee_id.user_id.lang if self.employee_id.user_id else None)
                or self.env.user.lang
                or self.env.context.get("lang")
                or "en_US"
            )
            decimal_point = getattr(lang, "decimal_point", ".") or "."
        except (ValueError, TypeError, AttributeError, KeyError):
            decimal_point = "."
        s = "%.2f" % (float(value or 0))
        return s.replace(".", decimal_point)

    def _get_my_timesheets_action_url(self):
        self.ensure_one()
        if not self.user_id:
            return False
        d = [
            ("date", "=", fields.Date.to_string(self.date)),
            ("user_id", "=", self.user_id.id),
        ]
        d += self._compliance_excluded_aal_domain_part(
            self.company_id or self.env.company
        )
        return self._moval_build_window_action_url(
            "moval_timesheet_compliance.action_moval_my_timesheets_by_date",
            "account.analytic.line",
            "list",
            d,
            self.company_id,
        )

    def _get_compliance_record_form_url(self):
        self.ensure_one()
        return self._moval_build_window_action_url(
            "moval_timesheet_compliance.action_moval_timesheet_compliance_manager",
            "timesheet.compliance",
            "form",
            None,
            self.company_id,
            res_id=self.id,
        )

    # Backward-compatible wrappers
    # -------------------------------------------------------------------------

    @api.model
    def _cron_send_employee_emails(self):
        """DEPRECATED: use _cron_send_b1_employee_daily_emails."""
        return self._cron_send_b1_employee_daily_emails()

    @api.model
    def _cron_send_daily_employee_emails(self):
        """DEPRECATED: use _cron_send_b1_employee_daily_emails."""
        return self._cron_send_b1_employee_daily_emails()

    def _get_project_hours_breakdown(self):
        self.ensure_one()
        aal = self.env["account.analytic.line"]
        domain = [("date", "=", self.date)]
        if "employee_id" in aal._fields:
            domain.append(("employee_id", "=", self.employee_id.id))
        else:
            domain.append(("user_id", "=", self.user_id.id))
        domain += self._compliance_excluded_aal_domain_part(
            self.company_id or self.env.company
        )

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
        domain += self._compliance_excluded_aal_domain_part(
            self.company_id or self.env.company
        )

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
                "hours": hours,
                "note": notes.get(task, ""),
            }
            for task, hours in totals.items()
        ]
        rows.sort(key=lambda r: r["hours"], reverse=True)
        return rows[:limit]

    @api.model
    def _cron_send_b2_manager_daily_emails(self):  # pylint: disable=too-many-locals
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

        for _dept_id, recs in by_dept.items():
            dept = recs[0].department_id
            manager_user = dept.manager_id.user_id if dept.manager_id else False
            manager_email = manager_user.email if manager_user else False
            email_to = self._moval_supervisor_email_to(manager_email)
            if not email_to:
                continue

            template = self.env.ref(
                "moval_timesheet_compliance."
                "mail_template_timesheet_compliance_b2_manager",
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
                "email_to_override": email_to,
            }
            subject = self._sanitize_mail_header(
                _("Timesheet compliance incidents - %(dept)s - %(date)s")
                % {
                    "dept": dept.display_name,
                    "date": fields.Date.to_string(target_date),
                }
            )
            email_from = (
                recs[0].company_id.email
                or self.env.user.email
                or "no-reply@example.com"
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
                    body=_("Included in the manager incident digest (B2) at %(when)s.")
                    % {
                        "when": fields.Datetime.to_string(fields.Datetime.now()),
                    },
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                )

        return True

    def _get_b2_department_action_url(self, department, target_date):

        employees = self.env["hr.employee"].search(
            [("department_id", "=", department.id)]
        )
        date_str = fields.Date.to_string(target_date)
        aal = self.env["account.analytic.line"]
        d = [("date", "=", date_str)]
        if "employee_id" in aal._fields:
            d.append(("employee_id", "in", employees.ids))
        else:
            d.append(("user_id", "in", employees.mapped("user_id").ids))
        comp = (self[:1].company_id if self else False) or (
            department.company_id or self.env.company
        )
        d += self._compliance_excluded_aal_domain_part(comp)
        return self._moval_build_window_action_url(
            "moval_timesheet_compliance.action_moval_my_timesheets_by_date",
            "account.analytic.line",
            "list",
            d,
            comp,
        )

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
        d = [("date", "=", fields.Date.to_string(self.date))]
        aal = self.env["account.analytic.line"]
        if "employee_id" in aal._fields:
            d.append(("employee_id", "=", self.employee_id.id))
        else:
            d.append(("user_id", "=", self.user_id.id))
        d += self._compliance_excluded_aal_domain_part(
            self.company_id or self.env.company
        )
        return self._moval_build_window_action_url(
            "moval_timesheet_compliance.action_moval_my_timesheets_by_date",
            "account.analytic.line",
            "list",
            d,
            self.company_id,
        )

    @api.model
    def _cron_send_b3_escalate_unresolved(self):
        today = fields.Date.context_today(self.env.user)
        now = fields.Datetime.now()
        deadline_48h = now - timedelta(hours=48)
        calendar_limit = today - timedelta(days=2)

        to_escalate = self.search(
            [
                ("state", "in", ["warn", "issue"]),
                ("escalated_at", "=", False),
                ("department_id", "!=", False),
                ("employee_id.x_timesheet_compliance_excluded", "=", False),
                "|",
                "&",
                ("incident_open_since", "!=", False),
                ("incident_open_since", "<=", deadline_48h),
                "&",
                ("incident_open_since", "=", False),
                ("date", "<=", calendar_limit),
            ]
        )
        if not to_escalate:
            return True

        template = self.env.ref(
            "moval_timesheet_compliance."
            "mail_template_timesheet_compliance_b3_escalation",
            raise_if_not_found=False,
        )

        for rec in to_escalate:
            rec.with_context(skip_compliance_incident_open_since_sync=True).write(
                {
                    "state": "escalated",
                    "escalated_at": now,
                    "incident_open_since": False,
                }
            )

            dept = rec.department_id
            manager_user = dept.manager_id.user_id if dept.manager_id else False
            manager_email = manager_user.email if manager_user else False
            if template:
                email_to = self._moval_supervisor_email_to(manager_email)
                if not email_to:
                    continue
                ctx = {
                    "email_to_override": email_to,
                    "detail_url": rec._get_b2_employee_day_url(),
                }

                email_from = (
                    rec.company_id.email
                    or self.env.user.email
                    or "no-reply@example.com"
                ).strip()
                email_from = email_from.replace("\n", " ").replace("\r", " ")

                subject = _("Timesheet compliance escalation - %(name)s - %(date)s") % {
                    "name": rec.employee_id.name,
                    "date": rec.date,
                }
                template.with_context(**ctx).send_mail(
                    rec.id,
                    force_send=True,
                    raise_exception=True,
                    email_values={
                        "email_from": email_from,
                        "email_to": email_to,
                        "subject": self._sanitize_mail_header(subject),
                    },
                )

            rec.message_post(
                body=_(
                    "Incident escalated (B3). The department manager was "
                    "notified at %(when)s."
                )
                % {
                    "when": fields.Datetime.to_string(fields.Datetime.now()),
                },
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )

        return True

    def action_mark_justified(self):
        self.write({"state": "justified"})

    @api.model
    def action_open_daily_compliance(self):
        """List view: yesterday and today (daily check)."""
        today = fields.Date.context_today(self.env.user)
        yesterday = today - timedelta(days=1)
        return self._get_compliance_list_action(
            [
                ("date", ">=", yesterday),
                ("date", "<=", today),
            ],
            "Timesheet compliance: last 2 days",
        )

    @api.model
    def action_open_compliance_today(self):
        """List view: today only."""
        today = fields.Date.context_today(self.env.user)
        return self._get_compliance_list_action(
            [("date", "=", today)],
            "Timesheet compliance: today",
        )

    @api.model
    def _moval_action_merge_context(self, action_read_dict, **extra_context):
        """Merge extra keys into an ir.actions.act_window dict's context (dict or string)."""
        if not action_read_dict:
            return action_read_dict
        ctx = action_read_dict.get("context")
        if isinstance(ctx, str):
            try:
                out = ast.literal_eval(ctx) if ctx.strip() else {}
            except (ValueError, SyntaxError, RecursionError):
                out = {}
        elif isinstance(ctx, dict):
            out = dict(ctx)
        else:
            out = {}
        out.update(extra_context)
        action_read_dict["context"] = out
        return action_read_dict

    @api.model
    def _get_compliance_list_action(self, domain, name, context_extra=None):
        """Return a window action for timesheet.compliance (domain, English title, context)."""
        action = self.env.ref(
            "moval_timesheet_compliance.action_moval_timesheet_compliance_manager",
            raise_if_not_found=False,
        )
        if not action:
            return {}
        result = action.read()[0]
        result["domain"] = domain
        result["name"] = name
        if context_extra:
            return self._moval_action_merge_context(result, **context_extra)
        return self._moval_action_merge_context(result)

    def action_open_timesheets(self):
        """Open timesheet lines for this employee and date (server-side domain)."""
        self.ensure_one()
        aal = self.env["account.analytic.line"]
        domain = [("date", "=", self.date)]
        if "employee_id" in aal._fields:
            domain.append(("employee_id", "=", self.employee_id.id))
        else:
            domain.append(("user_id", "=", self.user_id.id))
        domain += self._compliance_excluded_aal_domain_part(
            self.company_id or self.env.company
        )
        return {
            "type": "ir.actions.act_window",
            "name": "Timesheet lines: %s - %s" % (self.employee_id.name, self.date),
            "res_model": "account.analytic.line",
            "view_mode": "tree,form",
            "domain": domain,
            "target": "current",
            "context": {"default_date": self.date},
        }

    def action_open_attendances(self):
        """Open attendances for this employee on the same calendar day."""
        self.ensure_one()
        start_dt = fields.Datetime.to_datetime(self.date)
        end_dt = fields.Datetime.to_datetime(self.date + timedelta(days=1))
        return {
            "type": "ir.actions.act_window",
            "name": "Attendances: %s - %s" % (self.employee_id.name, self.date),
            "res_model": "hr.attendance",
            "view_mode": "tree,form",
            "domain": [
                ("employee_id", "=", self.employee_id.id),
                ("check_in", ">=", start_dt),
                ("check_in", "<", end_dt),
            ],
            "target": "current",
            "context": {"default_employee_id": self.employee_id.id},
        }

    @api.model
    def _cron_send_e3_weekly_generic_quality(self):  # pylint: disable=too-many-locals
        today = fields.Date.context_today(self.env.user)
        if fields.Date.to_date(today).weekday() != 0:
            return

        today = fields.Date.context_today(self.env.user)
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)

        depts = self.env["hr.department"].search([("manager_id", "!=", False)])

        template = self.env.ref(
            "moval_timesheet_compliance."
            "mail_template_timesheet_compliance_e3_weekly",
            raise_if_not_found=False,
        )
        if not template:
            return

        for dept in depts:
            manager_user = dept.manager_id.user_id
            manager_email = manager_user.email if manager_user else False
            email_to = self._moval_supervisor_email_to(manager_email)
            if not email_to:
                continue

            recs = self.search(
                [
                    ("department_id", "=", dept.id),
                    ("date", ">=", last_monday),
                    ("date", "<=", last_sunday),
                    ("employee_id.x_timesheet_compliance_excluded", "=", False),
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
            for _key, v in rows.items():
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
                {"email_to_override": email_to}
            )

            any_rec = recs[0]
            subject = self._sanitize_mail_header(
                _(
                    "Timesheet compliance: weekly generic allocation - %(dept)s - "
                    "%(date_from)s to %(date_to)s"
                )
                % {
                    "dept": dept.display_name,
                    "date_from": fields.Date.to_string(last_monday),
                    "date_to": fields.Date.to_string(last_sunday),
                }
            )

            email_from = self._sanitize_mail_header(
                any_rec.company_id.email
                or self.env.user.email
                or "no-reply@example.com"
            )

            template.with_context(**ctx).send_mail(
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
        if not dept:
            return False
        domain = [
            ("department_id", "=", dept.id),
            ("date", ">=", fields.Date.to_string(date_from)),
            ("date", "<=", fields.Date.to_string(date_to)),
        ]
        ctx = {
            "search_default_groupby_emp": 1,
            "search_default_groupby_date": 0,
        }
        return self._moval_build_window_action_url(
            "moval_timesheet_compliance.action_moval_timesheet_compliance_pivot",
            "timesheet.compliance",
            "pivot",
            domain,
            dept.company_id or self.env.company,
            context=ctx,
        )
