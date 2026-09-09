# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import UserError


class HrAttendanceBigButtonWizard(models.TransientModel):
    _name = "hr.attendance.big.button.wizard"
    _description = "Attendance Big Button Wizard"
    _rec_name = "employee_name"

    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        readonly=True,
        default=lambda self: self.env.user.employee_id,
    )
    employee_name = fields.Char(related="employee_id.name", readonly=True)
    employee_avatar_1920 = fields.Image(
        related="employee_id.avatar_1920", readonly=True
    )
    company_id = fields.Many2one(related="employee_id.company_id", readonly=True)
    attendance_state = fields.Selection(
        selection=[("checked_out", "Checked out"), ("checked_in", "Checked in")],
        compute="_compute_attendance_state",
        readonly=True,
    )
    reason_action_type = fields.Selection(
        selection=[("sign_in", "Sign in"), ("sign_out", "Sign out")],
        compute="_compute_reason_action_type",
        readonly=True,
    )
    next_action_text = fields.Char(compute="_compute_next_action_text", readonly=True)
    show_reason_on_attendance_screen = fields.Boolean(
        related="company_id.show_reason_on_attendance_screen",
        readonly=True,
    )
    show_reason_selector = fields.Boolean(
        compute="_compute_show_reason_selector",
        readonly=True,
    )
    required_reason_on_attendance_screen = fields.Boolean(
        related="company_id.required_reason_on_attendance_screen",
        readonly=True,
    )
    default_sign_in_reason_id = fields.Many2one(
        related="company_id.reason_on_attendance_screen_default_sign_in",
        readonly=True,
    )
    default_sign_out_reason_id = fields.Many2one(
        related="company_id.reason_on_attendance_screen_default_sign_out",
        readonly=True,
    )
    reason_id = fields.Many2one(
        "hr.attendance.reason",
        domain="[('show_on_attendance_screen', '=', True), ('action_type', '=', reason_action_type), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )

    def _compute_attendance_state(self):
        for record in self:
            record.attendance_state = record.env.user.attendance_state or "checked_out"

    @api.depends("attendance_state")
    def _compute_reason_action_type(self):
        for record in self:
            record.reason_action_type = (
                "sign_in" if record.attendance_state == "checked_out" else "sign_out"
            )

    @api.depends("reason_action_type")
    def _compute_next_action_text(self):
        for record in self:
            record.next_action_text = (
                record.env._("Entrada")
                if record.reason_action_type == "sign_in"
                else record.env._("Salida")
            )

    @api.depends("reason_action_type", "company_id")
    def _compute_show_reason_selector(self):
        reason_model = self.env["hr.attendance.reason"]
        for record in self:
            if not record.reason_action_type:
                record.show_reason_selector = False
                continue
            record.show_reason_selector = bool(
                reason_model.search_count(
                    [
                        ("show_on_attendance_screen", "=", True),
                        ("action_type", "=", record.reason_action_type),
                        "|",
                        ("company_id", "=", False),
                        ("company_id", "=", record.company_id.id),
                    ]
                )
            )

    @api.onchange(
        "attendance_state", "default_sign_in_reason_id", "default_sign_out_reason_id"
    )
    def _onchange_attendance_state(self):
        for record in self:
            if record.reason_id:
                continue
            if record.attendance_state == "checked_out":
                record.reason_id = record.default_sign_in_reason_id or self.env[
                    "hr.attendance.reason"
                ].search(
                    [
                        ("show_on_attendance_screen", "=", True),
                        ("action_type", "=", "sign_in"),
                        "|",
                        ("company_id", "=", False),
                        ("company_id", "=", record.company_id.id),
                    ],
                    limit=1,
                )
            else:
                record.reason_id = record.default_sign_out_reason_id or self.env[
                    "hr.attendance.reason"
                ].search(
                    [
                        ("show_on_attendance_screen", "=", True),
                        ("action_type", "=", "sign_out"),
                        "|",
                        ("company_id", "=", False),
                        ("company_id", "=", record.company_id.id),
                    ],
                    limit=1,
                )

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        if values.get("employee_id"):
            employee = self.env["hr.employee"].browse(values["employee_id"])
            values["reason_id"] = self._get_default_reason_for_employee(employee).id
            return values

        employee = self.env.user.employee_id
        if not employee:
            raise UserError(
                self.env._(
                    "Your user is not linked to an employee. "
                    "Please contact your administrator."
                )
            )
        values["employee_id"] = employee.id
        values["reason_id"] = self._get_default_reason_for_employee(employee).id
        return values

    @api.model
    def _get_default_reason_for_employee(self, employee):
        if not employee:
            return self.env["hr.attendance.reason"]

        action_type = (
            "sign_in" if employee.attendance_state == "checked_out" else "sign_out"
        )
        company = employee.company_id
        default_reason = (
            company.reason_on_attendance_screen_default_sign_in
            if action_type == "sign_in"
            else company.reason_on_attendance_screen_default_sign_out
        )
        if (
            default_reason
            and default_reason.show_on_attendance_screen
            and default_reason.action_type == action_type
            and (not default_reason.company_id or default_reason.company_id == company)
        ):
            return default_reason

        return self.env["hr.attendance.reason"].search(
            [
                ("show_on_attendance_screen", "=", True),
                ("action_type", "=", action_type),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )

    def action_toggle_attendance(self):
        self.ensure_one()
        employee = self.employee_id
        if not employee:
            raise UserError(
                self.env._(
                    "Your user is not linked to an employee. "
                    "Please contact your administrator."
                )
            )
        if (
            self.show_reason_selector
            and self.show_reason_on_attendance_screen
            and self.required_reason_on_attendance_screen
            and not self.reason_id
        ):
            raise UserError(self.env._("Please, select a reason."))

        context = {}
        if self.reason_id:
            context["attendance_reason_id"] = self.reason_id.id

        employee.with_context(
            **context
        )._attendance_action_change()  # pylint: disable=protected-access
        return {"type": "ir.actions.client", "tag": "reload"}

    @api.model
    def action_open_wizard(self):
        wizard = self.create({})
        return {
            "name": self.env._("Entrada / Salida"),
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "view_id": self.env.ref(
                "hr_attendance_big_button.view_hr_attendance_big_button_wizard_form"
            ).id,
            "target": "current",
            "res_id": wizard.id,
        }
