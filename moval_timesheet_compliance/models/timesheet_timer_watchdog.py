# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=protected-access,translation-not-lazy,too-many-arguments
# pylint: disable=too-many-positional-arguments,invalid-name

import logging
from datetime import timedelta

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class TimesheetTimerWatchdog(models.AbstractModel):
    _name = "timesheet.timer.watchdog"
    _description = "Timesheet Timer Watchdog"

    @api.model
    def cron_watchdog_timers(self):
        """Detect abnormal showing timers and create incidents.

        - Timer active longer than configured limit
        - Timer active without an active attendance
        - Auto-resolve incidents when the timer stops
        """
        now = fields.Datetime.now()

        timers = self._get_active_timers()
        active_refs = self._get_timer_ref_set(timers)

        resolved = self._auto_resolve_inactive_incidents(active_refs, now)
        if resolved:
            _logger.info("Timer watchdog: auto-resolved %s incident(s)", resolved)

        if not timers:
            return True

        for timer in timers:
            employee = self._get_timer_employee(timer)
            if not employee:
                continue
            if employee.x_timesheet_compliance_excluded:
                continue

            cfg = self._get_watchdog_config(employee=employee)

            started_at = self._get_timer_started_at(timer)
            if not started_at:
                continue

            duration_hours = (now - started_at).total_seconds() / 3600.0

            if cfg["max_active_hours"] and duration_hours >= cfg["max_active_hours"]:
                self._handle_incident(
                    timer=timer,
                    employee=employee,
                    incident_type="long_running",
                    timer_started_at=started_at,
                    duration_hours=duration_hours,
                    note=_("Timer active for %(duration)s (limit %(limit)s).")
                    % {
                        "duration": f"{duration_hours:.2f}h",
                        "limit": f"{cfg['max_active_hours']:.2f}h",
                    },
                    now=now,
                    cfg=cfg,
                )

            if cfg["check_no_attendance"] and not self._has_active_attendance(
                employee, now=now
            ):
                self._handle_incident(
                    timer=timer,
                    employee=employee,
                    incident_type="no_attendance",
                    timer_started_at=started_at,
                    duration_hours=duration_hours,
                    note=_("Timer active but no active attendance found."),
                    now=now,
                    cfg=cfg,
                )

        return True

    @api.model
    def handle_checkout(self, employee):
        """Checkout hook: create an incident for any running timer."""
        if employee.x_timesheet_compliance_excluded:
            return True
        now = fields.Datetime.now()
        cfg = self._get_watchdog_config(employee=employee)

        timers = self._get_active_timers(employee=employee)
        if not timers:
            return True

        for timer in timers:
            started_at = self._get_timer_started_at(timer)
            duration_hours = 0.0
            if started_at:
                duration_hours = (now - started_at).total_seconds() / 3600.0

            stopped = False
            if cfg["stop_on_checkout"]:
                stopped = self._try_stop_timer(timer)

            note = _("Checkout detected with an active timer.")
            if stopped:
                note += " " + _("Timer was automatically stopped.")
            else:
                note += " " + _("Please stop it and adjust your timesheet if needed.")

            self._handle_incident(
                timer=timer,
                employee=employee,
                incident_type="checkout_with_timer",
                timer_started_at=started_at,
                duration_hours=duration_hours,
                note=note,
                force_notify=True,
                now=now,
                cfg=cfg,
            )

        return True

    @api.model
    def _dept_timer_override_hours(self, value):
        """Return True if department set a positive override. Empty/False/0: company.

        Using ``is not None`` and ``>= 0`` alone is wrong for empty Odoo floats: unset
        fields are often False and ``(False is not None) and (False >= 0)`` is true, which
        would incorrectly override the company value.
        """
        return value is not None and value is not False and value > 0.0

    @api.model
    def _get_watchdog_config(self, employee=None):
        """Get watchdog config (company defaults + optional department overrides).

        For optional department timer fields, only a strictly positive value applies;
        empty, zero, or false means use the company setting.
        """
        company = self.env.company
        cfg = {
            "max_active_hours": company.x_timer_max_active_hours or 0.0,
            "notify_cooldown_hours": company.x_timer_notify_cooldown_hours or 0.0,
            "check_no_attendance": bool(company.x_timer_check_no_attendance),
            "stop_on_checkout": bool(company.x_timer_stop_on_checkout),
            "escalation_enabled": bool(company.x_timer_escalation_enabled),
            "escalation_after_count": company.x_timer_escalation_after_count or 0,
            "escalation_window_days": company.x_timer_escalation_window_days or 0,
            "escalation_cooldown_hours": company.x_timer_escalation_cooldown_hours
            or 0.0,
        }
        if employee and employee.department_id:
            dept = employee.department_id
            if self._dept_timer_override_hours(dept.x_timer_max_active_hours):
                cfg["max_active_hours"] = float(dept.x_timer_max_active_hours)
            if self._dept_timer_override_hours(dept.x_timer_notify_cooldown_hours):
                cfg["notify_cooldown_hours"] = float(dept.x_timer_notify_cooldown_hours)
        return cfg

    # Helpers
    # -------------------------------------------------------------------------

    def _get_timer_ref_set(self, timers):
        return {self._timer_ref_str(t) for t in timers}

    def _timer_ref_str(self, timer):
        return f"{timer._name},{timer.id}"

    def _incident_ref_str(self, incident):
        if not incident.timer_ref:
            return ""
        return self._timer_ref_str(incident.timer_ref)

    def _auto_resolve_inactive_incidents(self, active_refs, now):
        incident_model = self.env["timesheet.timer.incident"]
        open_incidents = incident_model.search([("is_resolved", "=", False)])

        to_resolve = open_incidents.filtered(
            lambda i: self._incident_ref_str(i) not in active_refs
        )
        if to_resolve:
            to_resolve.write({"is_resolved": True, "resolved_at": now})

        return len(to_resolve)

    # Timer adapter
    # -------------------------------------------------------------------------

    @api.model
    def _get_active_timers(self, employee=None):
        icp = self.env["ir.config_parameter"].sudo()
        model_name = icp.get_param("moval_timesheet.timer_model_name")

        if model_name and model_name in self.env:
            return self._get_active_timers_from_configured_model(
                model_name, icp=icp, employee=employee
            )

        if "project.task" in self.env:
            return self._get_active_timers_from_project_task(employee=employee)

        return self.env["ir.model"].browse()

    def _get_active_timers_from_configured_model(self, model_name, icp, employee=None):
        model = self.env[model_name]
        active_field = (
            icp.get_param("moval_timesheet.timer_active_field") or "is_timer_running"
        )
        domain = [(active_field, "=", True)]

        if employee:
            emp_field = (
                icp.get_param("moval_timesheet.timer_employee_field") or "employee_id"
            )
            if emp_field in model._fields:
                domain.append((emp_field, "=", employee.id))
            elif "user_id" in model._fields and employee.user_id:
                domain.append(("user_id", "=", employee.user_id.id))

        return model.search(domain)

    def _get_active_timers_from_project_task(self, employee=None):
        task = self.env["project.task"]
        if "is_timer_running" not in task._fields:
            return task.browse()

        domain = [("is_timer_running", "=", True)]
        if employee:
            if "employee_id" in task._fields:
                domain.append(("employee_id", "=", employee.id))
            elif employee.user_id and "user_id" in task._fields:
                domain.append(("user_id", "=", employee.user_id.id))

        return task.search(domain)

    def _get_timer_started_at(self, timer):
        icp = self.env["ir.config_parameter"].sudo()
        configured_model = icp.get_param("moval_timesheet.timer_model_name") or ""
        if timer._name == configured_model:
            start_field = (
                icp.get_param("moval_timesheet.timer_start_field") or "timer_start"
            )
            return getattr(timer, start_field, False)

        return getattr(timer, "timer_start", False) or getattr(
            timer, "date_start", False
        )

    def _get_timer_employee(self, timer):
        icp = self.env["ir.config_parameter"].sudo()
        configured_model = icp.get_param("moval_timesheet.timer_model_name") or ""
        if timer._name == configured_model:  # noqa: W0212
            emp_field = (
                icp.get_param("moval_timesheet.timer_employee_field") or "employee_id"
            )
            employee = getattr(timer, emp_field, False)
            if employee:
                return employee
            return self._employee_from_user(getattr(timer, "user_id", False))

        employee = getattr(timer, "employee_id", False)
        if employee:
            return employee
        return self._employee_from_user(getattr(timer, "user_id", False))

    def _employee_from_user(self, user):
        if not user:
            return False
        return self.env["hr.employee"].search([("user_id", "=", user.id)], limit=1)

    def _try_stop_timer(self, timer):
        for method_name in (
            "action_timer_stop",
            "action_stop_timer",
            "action_timer_pause",
            "action_pause_timer",
        ):
            method = getattr(timer, method_name, None)
            if method:
                method()
                return True
        return False

    # Attendance
    # -------------------------------------------------------------------------

    def _has_active_attendance(self, employee, now):
        return bool(
            self.env["hr.attendance"].search(
                [
                    ("employee_id", "=", employee.id),
                    ("check_in", "<=", now),
                    ("check_out", "=", False),
                ],
                limit=1,
            )
        )

    # Incidents + notifications + escalation
    # -------------------------------------------------------------------------

    def _handle_incident(
        self,
        timer,
        employee,
        incident_type,
        timer_started_at=False,
        duration_hours=0.0,
        note=False,
        force_notify=False,
        now=False,
        cfg=False,
    ):
        incident_model = self.env["timesheet.timer.incident"].sudo()
        now = now or fields.Datetime.now()
        cfg = cfg or self._get_watchdog_config()

        timer_ref = self._timer_ref_str(timer)
        incident = incident_model.search(
            [
                ("timer_ref", "=", timer_ref),
                ("incident_type", "=", incident_type),
                ("is_resolved", "=", False),
            ],
            limit=1,
        )

        vals = {
            "last_seen_at": now,
            "timer_started_at": timer_started_at,
            "duration_hours": duration_hours,
        }

        if incident:
            if not vals["timer_started_at"]:
                vals.pop("timer_started_at")
            incident.write(vals)
        else:
            vals.update(
                {
                    "timer_ref": timer_ref,
                    "employee_id": employee.id,
                    "company_id": employee.company_id.id or self.env.company.id,
                    "incident_type": incident_type,
                    "first_seen_at": now,
                    "note": note or "",
                }
            )
            incident = incident_model.create(vals)
            _logger.info(
                "Timer watchdog: incident created (%s) for %s", incident_type, timer_ref
            )

        did_notify_employee = False
        if force_notify or self._should_notify(
            incident, cfg["notify_cooldown_hours"], now=now
        ):
            did_notify_employee = self._notify_and_mark(employee, incident, now)
            if did_notify_employee:
                _logger.info(
                    "Timer watchdog: employee notified (%s) for %s",
                    incident_type,
                    timer_ref,
                )

        if cfg["escalation_enabled"]:
            self._maybe_escalate_to_manager(
                employee=employee,
                incident=incident,
                now=now,
                cfg=cfg,
                did_notify_employee=did_notify_employee,
            )

        return incident

    def _notify_and_mark(self, employee, incident, now):
        if not self._notify_employee(employee, incident):
            return False
        incident.write(
            {
                "last_notified_at": now,
                "notify_count": incident.notify_count + 1,
            }
        )
        # Flush so that a subsequent search in the same transaction sees the update
        # (e.g. second cron run must respect cooldown).
        incident.flush_recordset(["last_notified_at", "notify_count"])
        return True

    def _should_notify(self, incident, cooldown_hours, now=False):
        now = now or fields.Datetime.now()
        if not cooldown_hours or not incident.last_notified_at:
            return True
        return now >= (incident.last_notified_at + timedelta(hours=cooldown_hours))

    def _notify_employee(self, employee, incident):
        user = employee.user_id
        if not user:
            return False

        summary_map = {
            "long_running": _("Timer watchdog: timer running too long"),
            "no_attendance": _("Timer watchdog: timer running without attendance"),
            "checkout_with_timer": _("Timer watchdog: checkout with an active timer"),
        }
        summary = summary_map.get(
            incident.incident_type,
            _("Timer watchdog: please review your running timer"),
        )

        self.env["mail.activity"].sudo().create(
            {
                "res_model_id": self.env["ir.model"]._get_id(
                    "timesheet.timer.incident"
                ),
                "res_id": incident.id,
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "summary": summary,
                "note": incident.note or "",
                "user_id": user.id,
            }
        )
        return True

    def _maybe_escalate_to_manager(
        self, employee, incident, now, cfg, did_notify_employee
    ):
        if not did_notify_employee or not cfg["escalation_after_count"]:
            return False

        window_start = now - timedelta(days=cfg["escalation_window_days"])
        incident_model = self.env["timesheet.timer.incident"]
        recent = incident_model.search(
            [
                ("employee_id", "=", employee.id),
                ("incident_type", "=", incident.incident_type),
                ("last_notified_at", ">=", window_start),
            ]
        )
        total_notify = sum(recent.mapped("notify_count")) or incident.notify_count
        if total_notify < cfg["escalation_after_count"]:
            return False

        if incident.escalated_at and cfg["escalation_cooldown_hours"]:
            if now < incident.escalated_at + timedelta(
                hours=cfg["escalation_cooldown_hours"]
            ):
                return False

        manager_user = self._get_manager_user(employee)
        if not manager_user:
            return False

        summary = _("Timer watchdog escalation: recurring incident")
        note = _(
            "Recurring timer incident for %(emp)s.\n\nType: %(type)s\n"
            "Notifications in last %(days)s days: %(count)s\n\nLast note:\n%(note)s"
        ) % {
            "emp": employee.name,
            "type": incident.incident_type,
            "days": cfg["escalation_window_days"],
            "count": total_notify,
            "note": incident.note or "",
        }

        self.env["mail.activity"].sudo().create(
            {
                "res_model_id": self.env["ir.model"]._get_id(  # noqa: W0212
                    "timesheet.timer.incident"
                ),
                "res_id": incident.id,
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "summary": summary,
                "note": note,
                "user_id": manager_user.id,
            }
        )

        incident.write(
            {
                "escalated_at": now,
                "escalated_count": incident.escalated_count + 1,
            }
        )
        _logger.warning(
            "Timer watchdog: escalated incident (%s) for %s",
            incident.incident_type,
            incident.timer_ref,
        )
        return True

    def _get_manager_user(self, employee):
        dept = employee.department_id
        if dept and dept.manager_id and dept.manager_id.user_id:
            return dept.manager_id.user_id

        hr_manager_group = self.env.ref("hr.group_hr_manager", raise_if_not_found=False)
        if hr_manager_group and hr_manager_group.users:
            return hr_manager_group.users[0]

        return False
