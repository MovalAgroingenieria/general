# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrRoleAssignment(models.Model):
    _name = "hr.role.assignment"
    _description = "Employee Role Assignment"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date_start desc"

    role_id = fields.Many2one(
        "hr.role",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )

    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )

    date_start = fields.Date(
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )

    state = fields.Selection(
        [
            ("draft", _("Draft")),
            ("validated", _("Validated")),
            ("assigned", _("Achieved/In Progress")),
        ],
        default="draft",
        tracking=True,
    )

    note = fields.Html(
        string="Notes",
    )

    assigned_by = fields.Many2one(
        'res.users',
        string='Assigned By',
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )

    display_name_with_dept = fields.Char(
        string="Role with Department",
        compute="_compute_display_name_with_dept",
        store=True,
    )

    @api.constrains("employee_id", "role_id", "date_start", "state")
    def _check_no_overlap(self):
        for rec in self:
            if rec.state != "draft":
                domain = [
                    ("employee_id", "=", rec.employee_id.id),
                    ("role_id", "=", rec.role_id.id),
                    ("state", "!=", "draft"),
                    ("id", "!=", rec.id),
                ]
                if self.search_count(domain):
                    raise ValidationError(
                        _("The employee already has this role assigned."))

    @api.depends('role_id', 'role_id.department_id')
    def _compute_display_name_with_dept(self):
        for rec in self:
            role_name = rec.role_id.name or ''
            dept_name = rec.role_id.department_id.name or ''
            rec.display_name_with_dept = \
                f"{role_name} - {dept_name}" if dept_name else role_name

    def name_get(self):
        result = []
        for record in self:
            display_name = _("Assignment %s") % (record.id or '')
            result.append((record.id, display_name))
        return result
