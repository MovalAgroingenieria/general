# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import base64
import re
from datetime import date, datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_date


class HrTeleworkDay(models.Model):
    _name = 'hr.telework.day'
    _description = 'Day Declaration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date desc, employee_id'

    name = fields.Char(
        compute='_compute_name',
        store=True,
    )

    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        index=True,
        tracking=True,
    )

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='User',
        related='employee_id.user_id',
        store=True,
        index=True,
    )

    department_id = fields.Many2one(
        comodel_name='hr.department',
        string='Department',
        required=True,
        index=True,
        tracking=True,
    )

    workstation_id = fields.Many2one(
        comodel_name='office.workstation',
        string='Workstation',
        index=True,
        tracking=True,
        help='Workstation assigned for this day',
    )

    date = fields.Date(
        string='Date',
        required=True,
        index=True,
        tracking=True,
    )

    date_display = fields.Char(
        string='Date Display',
        compute='_compute_date_display',
        store=True,
    )

    create_date = fields.Datetime(
        string='Creation Date', readonly=True,
        help='Date and time when the declaration was created',
    )

    mode = fields.Selection([
            ('remote', 'Remote Work'),
            ('onsite', 'On-site'),
        ],
        required=True,
        default='onsite',
        tracking=True,
    )

    mode_icon = fields.Char(
        string='Mode Icon',
        compute='_compute_mode_icon',
        store=True,
    )

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('pending_review', 'Pending Review'),
            ('confirmed', 'Confirmed'),
        ],
        string='State',
        default='draft',
        tracking=True,
        index=True,
    )

    note = fields.Text(
        string='Note',
        translate=True,
    )
    source = fields.Selection([
            ('self', 'Employee'),
            ('manager', 'Manager'),
            ('auto_rule', 'Automatic Rule'),
        ],
        default='self',
        tracking=True,
    )

    overbooked = fields.Boolean(
        readonly=True, copy=False, tracking=True,
        help='Marked if confirmation exceeds capacity (flexible mode).',
    )

    total_availability = fields.Char(
        string='Total Avail.',
        help='Total company availability',
    )

    total_status_color = fields.Selection([
            ('green', 'Available'),
            ('yellow', 'Full'),
            ('red', 'Overbooked'),
        ],
        string='Total Color',
        default='green',
    )

    total_overbooked = fields.Boolean(
        string='Total Overbooked',
        default=False,
        help='Total company capacity exceeded',
    )

    office_availability = fields.Text(
        string='Availability by Office',
        compute='_compute_office_availability',
        store=False,
        help='Detailed availability information by office',
    )

    is_this_week = fields.Boolean(
        string='This Week',
        compute='_compute_week_flags',
        search='_search_this_week',
        store=False
    )

    is_next_week = fields.Boolean(
        string='Next Week',
        compute='_compute_week_flags',
        search='_search_next_week',
        store=False
    )

    percentage_telework = fields.Float(
        string='Telework Percentage',
        compute='_compute_percentage_telework',
        store=True,
        help='Telework percentage (100 if remote, 0 if on-site)',
    )

    has_workstation_conflict = fields.Boolean(
        string='Has Workstation Conflict',
        compute='_compute_workstation_conflicts',
        store=False,
        help='True if this workstation is occupied by other declarations',
    )

    conflicting_declaration_ids = fields.Many2many(
        comodel_name='hr.telework.day',
        relation='hr_telework_conflict_rel',
        column1='declaration_id',
        column2='conflicting_id',
        string='Conflicting Declarations',
        compute='_compute_workstation_conflicts',
        store=False,
        help='Other declarations using the same workstation on the same date',
    )

    _sql_constraints = [
        ('uniq_emp_date', 'unique(employee_id, date)',
         'A declaration already exists for this employee and date.'),
    ]

    @api.model
    def _get_manager_emails(self):
        """Get email addresses of telework and HR managers."""
        manager_group = self.env.ref(
            'hr_telework_tracking_site_capacity.group_telework_manager',
            raise_if_not_found=False,
        )
        hr_manager_group = self.env.ref(
            'hr.group_hr_manager', raise_if_not_found=False
        )

        users = self.env['res.users']
        if manager_group:
            users |= manager_group.users
        if hr_manager_group:
            users |= hr_manager_group.users

        return sorted({user.email for user in users if user.email})

    @api.depends('employee_id', 'mode')
    def _compute_name(self):
        for rec in self:
            mode_dict = dict(
                self._fields['mode']._description_selection(self.env)
            )
            mode_name = mode_dict.get(rec.mode, rec.mode)
            rec.name = f"{rec.employee_id.name or 'N/A'} - {mode_name}"

    @api.depends('workstation_id', 'date', 'mode', 'state')
    def _compute_workstation_conflicts(self):
        """Compute workstation conflicts for each record"""
        for rec in self:
            if (not rec.workstation_id or rec.mode != 'onsite' or
                    rec.state not in ['confirmed', 'draft', 'pending_review']):
                rec.has_workstation_conflict = False
                rec.conflicting_declaration_ids = [(6, 0, [])]
                continue

            domain = [
                ('date', '=', rec.date),
                ('workstation_id', '=', rec.workstation_id.id),
                ('mode', '=', 'onsite'),
                ('state', 'in', ['confirmed', 'draft', 'pending_review']),
            ]

            if rec.id and str(rec.id).isdigit():
                domain.append(('id', '!=', rec.id))

            conflicting_records = self.search(domain)

            rec.has_workstation_conflict = bool(conflicting_records)
            rec.conflicting_declaration_ids = [(6, 0, conflicting_records.ids)]

    @api.depends('date', 'mode')
    def _compute_office_availability(self):
        """Compute availability information by office"""
        Office = self.env['office.location'].sudo()
        Workstation = self.env['office.workstation'].sudo()
        TeleworkDay = self.env['hr.telework.day'].sudo()

        for rec in self:
            if not rec.date or rec.mode == 'remote':
                rec.office_availability = ''
                continue

            offices = Office.search([
                ('active', '=', True)
            ], order='name')

            office_info = []
            total_occupied = 0
            total_workstations = 0

            for office in offices:
                office_workstations = Workstation.search_count([
                    ('office_id', '=', office.id),
                    ('active', '=', True)
                ])

                occupied = TeleworkDay.search_count([
                    ('date', '=', rec.date),
                    ('mode', '=', 'onsite'),
                    ('state', 'in', ['confirmed', 'draft', 'pending_review']),
                    ('workstation_id.office_id', '=', office.id)
                ])

                total_occupied += occupied
                total_workstations += office_workstations

                if office_workstations > 0:
                    percentage = round((occupied / office_workstations) * 100)
                    if percentage >= 100:
                        color = 'danger'
                    elif percentage >= 80:
                        color = 'warning'
                    else:
                        color = 'success'

                    office_text = {
                        'name': office.name,
                        'occupied': occupied,
                        'total': office_workstations,
                        'percentage': percentage,
                        'color': color
                    }
                else:
                    office_text = {
                        'name': office.name,
                        'occupied': occupied,
                        'total': office_workstations,
                        'percentage': 0,
                        'color': 'secondary'
                    }

                office_info.append(office_text)

            if office_info:
                if total_workstations > 0:
                    total_percentage = round(
                        (total_occupied / total_workstations) * 100
                    )
                else:
                    total_percentage = 0

                html_rows = []
                for office in office_info:
                    color_class = f"text-{office['color']}"
                    progress_width = office['percentage']

                    row = f"""
                    <tr>
                        <td><strong>{office['name']}</strong></td>
                        <td class="{color_class}">
                            {office['occupied']}/{office['total']}
                        </td>
                        <td>
                            <div class="progress" style="height: 20px;">
                                <div class="progress-bar bg-{office['color']}"
                                     style="width: {progress_width}%;">
                                    {office['percentage']}%
                                </div>
                            </div>
                        </td>
                    </tr>
                    """
                    html_rows.append(row)

                if total_workstations > 0:
                    if total_percentage >= 100:
                        total_color = 'danger'
                    elif total_percentage >= 80:
                        total_color = 'warning'
                    else:
                        total_color = 'success'
                else:
                    total_color = 'secondary'

                total_color_class = f"text-{total_color}"

                separator = """
                    <tr>
                        <td colspan="3" class="pt-2 pb-1">
                            <hr class="my-1"/>
                        </td>
                    </tr>
                """
                total_row = f"""
                    <tr class="table-active">
                        <td><strong>{_('Total')}</strong></td>
                        <td class="{total_color_class}">
                            {total_occupied}/{total_workstations}
                        </td>
                        <td>
                            <div class="progress" style="height: 20px;">
                                <div class="progress-bar bg-{total_color}"
                                     style="width: {total_percentage}%;">
                                    {total_percentage}%
                                </div>
                            </div>
                        </td>
                    </tr>
                """

                html_rows.append(separator)
                html_rows.append(total_row)

                html_content = f"""
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>{_('Office')}</th>
                            <th>{_('Occupied')}</th>
                            <th>{_('Status')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(html_rows)}
                    </tbody>
                </table>
                """
                rec.office_availability = html_content
            else:
                rec.office_availability = (
                    f'<p class="text-muted">{_("No offices configured")}</p>'
                )

    @api.depends('date')
    def _compute_date_display(self):
        """Compute date display with weekday name"""
        for rec in self:
            if rec.date:
                weekday = format_date(
                    self.env, rec.date, date_format='EEE'
                ).capitalize()
                rec.date_display = (
                    f"{weekday} {rec.date.strftime('%d/%m/%Y')}"
                )
            else:
                rec.date_display = ''

    @api.depends('mode')
    def _compute_mode_icon(self):
        """Compute icon for mode display"""
        for rec in self:
            if rec.mode == 'remote':
                rec.mode_icon = 'fa-home'
            elif rec.mode == 'onsite':
                rec.mode_icon = 'fa-building'
            else:
                rec.mode_icon = ''

    @api.depends('mode')
    def _compute_percentage_telework(self):
        """Compute percentage for statistics"""
        for rec in self:
            rec.percentage_telework = 100.0 if rec.mode == 'remote' else 0.0

    @api.depends('date')
    def _compute_week_flags(self):
        """Compute week flags for dynamic filters"""
        today = date.today()
        monday_this_week = today - timedelta(days=today.weekday())
        sunday_this_week = monday_this_week + timedelta(days=6)
        monday_next_week = monday_this_week + timedelta(days=7)
        sunday_next_week = monday_next_week + timedelta(days=6)

        for rec in self:
            if rec.date:
                rec.is_this_week = (
                    monday_this_week <= rec.date <= sunday_this_week)
                rec.is_next_week = (
                    monday_next_week <= rec.date <= sunday_next_week)
            else:
                rec.is_this_week = False
                rec.is_next_week = False

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Set default department when employee changes"""
        if self.employee_id and self.employee_id.department_id:
            self.department_id = self.employee_id.department_id

    def _update_availability_info(self):
        """Update availability information efficiently - enhanced version"""
        if not self:
            return

        date_groups = {}
        for rec in self:
            if rec.date:
                if rec.date not in date_groups:
                    date_groups[rec.date] = []
                date_groups[rec.date].append(rec)

        for date, records in date_groups.items():
            self._bulk_update_availability_for_date(date, records)

    def force_refresh_availability(self):
        """Force refresh of availability data for current records"""
        self._update_availability_info()

    def action_confirm(self):
        current_user = self.env.user
        is_manager = (
            current_user.has_group(
                'hr_telework_tracking_site_capacity.group_telework_manager'
            ) or current_user.has_group('hr.group_hr_manager')
        )

        if not is_manager:
            raise UserError(
                _('Only managers can confirm telework declarations.')
            )

        for rec in self:
            if rec.has_workstation_conflict:
                raise UserError(
                    _('Cannot confirm declaration: the workstation is '
                      'already occupied by another declaration on the '
                      'same date.')
                )

        Param = self.env['ir.config_parameter'].sudo()
        policy = Param.get_param(
            'hr_telework_tracking_site_capacity.capacity_policy', 'flexible')
        for rec in self:
            rec._check_cutoff_on_confirm()
            over = rec._check_and_mark_capacity_overflow()
            if policy == 'strict' and over:
                raise UserError(
                    _('Capacity exceeded for %s (%s).') % (
                        rec.department_id.name, rec.date))
            rec.write({'state': 'confirmed', 'overbooked': bool(over)})

            self._refresh_capacity_display()
            self._compute_availability_fields()

            if over:
                rec._notify_overbooked()
                self.env['bus.bus']._sendone(
                    self.env.user.partner_id,
                    'display_notification',
                    {
                        'title': _('Attention! Capacity Exceeded'),
                        'message': _(
                            'The capacity of department %s for %s '
                            'has been exceeded. It is recommended to review '
                            'the assignments.') % (
                            rec.department_id.name, rec.date_display),
                        'type': 'warning',
                        'sticky': True,
                    }
                )
        self.invalidate_recordset()
        return True

    def _refresh_capacity_display(self):
        """Update capacity info for related records efficiently"""
        for rec in self:
            related_records = self.search([
                ('date', '=', rec.date),
                ('department_id', '=', rec.department_id.id),
            ])
            for record in related_records:
                record._update_availability_info()
            other_records = self.search([
                ('date', '=', rec.date),
                ('department_id', '!=', rec.department_id.id),
            ])
            other_records._update_availability_info()

    def action_set_draft(self):
        current_user = self.env.user
        is_manager = (
            current_user.has_group(
                'hr_telework_tracking_site_capacity.group_telework_manager'
            ) or current_user.has_group('hr.group_hr_manager')
        )

        if not is_manager:
            raise UserError(
                _('Only managers can change the state of declarations.')
            )

        for rec in self:
            rec.write({'state': 'draft'})
            rec._refresh_capacity_display()
            rec._compute_availability_fields()

    def _check_cutoff_on_confirm(self):
        """Check if confirmation is allowed according to cutoff day and time"""
        Param = self.env['ir.config_parameter'].sudo()
        cutoff_weekday = int(Param.get_param(
            'hr_telework_tracking_site_capacity.cutoff_weekday', '4'
        ))
        cutoff_time = float(Param.get_param(
            'hr_telework_tracking_site_capacity.cutoff_time', '18.0'))

        cutoff_hour = int(cutoff_time)
        cutoff_minute = int((cutoff_time % 1) * 60)

        now = datetime.now()

        for rec in self:
            if rec.date == now.date():
                continue

            if rec.date < now.date():
                raise UserError(
                    f'Cannot confirm a declaration for a past date '
                    f'({rec.date_display})')

            days_since_monday = now.weekday()

            days_to_cutoff = cutoff_weekday - days_since_monday
            if days_to_cutoff < 0:
                days_to_cutoff += 7

            cutoff_dt = now.replace(
                hour=cutoff_hour,
                minute=cutoff_minute,
                second=0,
                microsecond=0
            ) + timedelta(days=days_to_cutoff)

            next_week_start = now.date() + timedelta(days=7)
            if now > cutoff_dt and rec.date >= next_week_start:
                if not self.env.user.has_group('hr.group_hr_manager'):
                    weekday_names = [
                        'Monday', 'Tuesday', 'Wednesday', 'Thursday',
                        'Friday', 'Saturday', 'Sunday']
                    cutoff_day_name = weekday_names[cutoff_weekday]
                    raise UserError(
                        f'Cannot confirm after {cutoff_day_name} at '
                        f'{cutoff_hour:02d}:{cutoff_minute:02d} for next '
                        f'week declarations. Target date: {rec.date_display}')

        return True

    def _notify_overbooked(self):
        """Notify about capacity overflow - only visual notification in UI"""
        pass

    def _get_department_capacity(self, date, department):
        """Get department capacity from office workstations.

        Searches for total capacity of workstations available
        for the department in all offices.
        Only counts stations available for booking on the given date.
        If no stations are configured, uses the global default capacity.
        """
        if not self._is_date_available_for_booking(date):
            return 0

        offices = self.env['office.location'].search([('active', '=', True)])
        total_capacity = 0

        for office in offices:
            workstations = self.env['office.workstation'].search([
                ('office_id', '=', office.id),
                ('active', '=', True)
            ])

            if department:
                dept_workstations = workstations.filtered(
                    lambda w: w.department_id == department)
                if dept_workstations:
                    total_capacity += len(dept_workstations)
                else:
                    generic_workstations = workstations.filtered(
                        lambda w: not w.department_id)
                    total_capacity += len(generic_workstations)
            else:
                total_capacity += len(workstations)

        if total_capacity == 0:
            param_name = ('hr_telework_tracking_site_capacity.'
                          'default_capacity_full_day')
            global_capacity = int(
                self.env['ir.config_parameter'].sudo().get_param(
                    param_name, '0'))
            return global_capacity

        return total_capacity

    def _is_date_available_for_booking(self, target_date):
        """
        Check if a date is available for new bookings
        based on cutoff time configuration.
        """
        try:
            config_param = self.env['ir.config_parameter'].sudo()
            cutoff_weekday_param = config_param.get_param(
                'hr_telework_tracking_site_capacity.cutoff_weekday')
            cutoff_time_param = config_param.get_param(
                'hr_telework_tracking_site_capacity.cutoff_time')

            if not cutoff_weekday_param:
                return True

            from datetime import datetime, timedelta

            cutoff_weekday = int(cutoff_weekday_param)
            cutoff_time = float(cutoff_time_param or 18.0)

            if isinstance(target_date, str):
                target_date = fields.Date.from_string(target_date)

            days_since_monday = target_date.weekday()
            monday_of_target_week = target_date - timedelta(
                days=days_since_monday)

            cutoff_date = monday_of_target_week + timedelta(
                days=cutoff_weekday)

            cutoff_hour = int(cutoff_time)
            cutoff_minute = int((cutoff_time - cutoff_hour) * 60)

            cutoff_datetime = datetime.combine(
                cutoff_date,
                datetime.min.time().replace(
                    hour=cutoff_hour,
                    minute=cutoff_minute
                ))
            now = datetime.now()
            return now <= cutoff_datetime

        except Exception:
            return True

    def _check_and_mark_capacity_overflow(self):
        self.ensure_one()
        if self.mode != 'onsite':
            return False
        cap = self._get_department_capacity(self.date, self.department_id)
        count = self.search_count([
            ('id', '!=', self.id),
            ('state', '=', 'confirmed'),
            ('mode', '=', 'onsite'),
            ('department_id', '=', self.department_id.id),
            ('date', '=', self.date),
        ])
        return (count + 1) > cap

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to invalidate computed fields of related records"""
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        for vals in vals_list:
            if 'employee_id' in vals and 'department_id' not in vals:
                employee = self.env['hr.employee'].browse(vals['employee_id'])
                if employee.department_id:
                    vals['department_id'] = employee.department_id.id

        records = super().create(vals_list)

        newly_pending = self.browse()
        for vals, record in zip(vals_list, records):
            is_pending = vals.get('state') == 'pending_review'
            if is_pending and record.state == 'pending_review':
                newly_pending |= record

        if newly_pending:
            newly_pending._notify_managers_pending_review_state()

        dates_affected = set(rec.date for rec in records if rec.date)
        if dates_affected:
            for date in dates_affected:
                date_records = self.search([('date', '=', date)])
                if date_records:
                    self._bulk_update_availability_for_date(date, date_records)

        return records

    def write(self, vals):
        """Override write to maintain data integrity and track user changes"""
        old_data = []
        for rec in self:
            old_data.append({
                'id': rec.id,
                'old_date': rec.date,
                'old_department_id': (
                    rec.department_id.id if rec.department_id else False
                ),
                'old_employee_id': (
                    rec.employee_id.id if rec.employee_id else False
                ),
                'old_workstation_id': (
                    rec.workstation_id.id if rec.workstation_id else False
                ),
                'old_mode': rec.mode,
                'old_state': rec.state,
            })

        previous_states = {
            data['id']: data['old_state'] for data in old_data if data['id']
        }

        current_user = self.env.user
        is_manager = (
            current_user.has_group(
                'hr_telework_tracking_site_capacity.group_telework_manager'
            ) or current_user.has_group('hr.group_hr_manager')
        )

        user_records = self.filtered(
            lambda rec: rec.employee_id.user_id == current_user
        ) if not is_manager else self.browse()

        technical_fields = {
            'message_follower_ids', 'activity_ids', 'message_ids',
            'display_name', '__last_update'
        }
        meaningful_changes = any(
            field not in technical_fields for field in vals.keys()
        )

        if (
            not is_manager
            and user_records
            and len(user_records) == len(self)
            and meaningful_changes
            and not self.env.context.get('skip_pending_review_transition')
        ):
            if 'state' not in vals:
                vals = dict(vals)
                vals['state'] = 'pending_review'

        if not is_manager and vals:
            relevant_changes = {
                k: v for k, v in vals.items()
                if k in ['mode', 'workstation_id', 'note']
            }
            if relevant_changes:
                for rec in self:
                    if rec.state in ['draft', 'pending_review']:
                        changes_str = ', '.join([
                            f"{k}: {v}" for k, v in relevant_changes.items()
                        ])
                        message = _(
                            "Declaration modified by user: %s"
                        ) % changes_str
                        rec.message_post(
                            body=message, message_type='notification'
                        )

        result = super().write(vals)

        if 'state' in vals:
            newly_pending = self.filtered(
                lambda rec: (
                    rec.state == 'pending_review'
                    and previous_states.get(rec.id) != 'pending_review'
                )
            )
            if newly_pending:
                newly_pending._notify_managers_pending_review_state()

        critical_fields = [
            'date', 'employee_id', 'workstation_id', 'mode', 'state'
        ]

        if any(field in vals for field in critical_fields):
            if 'workstation_id' in vals or 'date' in vals or 'state' in vals:
                self.invalidate_recordset(['has_workstation_conflict',
                                          'conflicting_declaration_ids'])

                if 'workstation_id' in vals or 'date' in vals:
                    workstation_ids = [vals.get('workstation_id')] + [
                        rec.workstation_id.id for rec in self
                        if rec.workstation_id
                    ]
                    related_records = self.search([
                        ('date', 'in', [rec.date for rec in self]),
                        ('workstation_id', 'in', workstation_ids),
                        ('id', 'not in', self.ids)
                    ])
                    if related_records:
                        related_records.invalidate_recordset([
                            'has_workstation_conflict',
                            'conflicting_declaration_ids'
                        ])

            availability_fields = ['workstation_id', 'state', 'date', 'mode']
            if any(field in vals for field in availability_fields):
                self._update_related_availability_data(old_data, vals)

        return result

    def _compute_availability_fields(self):
        """Force recomputation of total availability only - optimized"""
        dates_affected = set(rec.date for rec in self if rec.date)

        if dates_affected:
            all_affected = self.search([
                ('date', 'in', list(dates_affected))
            ])

            if all_affected:
                all_affected.invalidate_recordset([
                    'total_availability',
                    'total_status_color',
                    'total_overbooked',
                ])

                all_affected._update_availability_info()

    def _update_related_availability_data(self, old_data, new_vals):
        """Update availability data for all related records after changes"""
        dates_to_update = set()
        departments_to_update = set()

        for i, rec in enumerate(self):
            old_info = old_data[i]

            if old_info['old_date']:
                dates_to_update.add(old_info['old_date'])
            if rec.date:
                dates_to_update.add(rec.date)

            if old_info['old_department_id']:
                departments_to_update.add(old_info['old_department_id'])
            if rec.department_id:
                departments_to_update.add(rec.department_id.id)

        if dates_to_update:
            affected_records = self.search([
                ('date', 'in', list(dates_to_update)),
            ])

            for date in dates_to_update:
                date_records = affected_records.filtered(
                    lambda record: record.date == date)
                if date_records:
                    self._bulk_update_availability_for_date(date, date_records)

    def _bulk_update_availability_for_date(self, target_date, records):
        """Efficiently refresh availability for all records on a date."""
        if not target_date or not records:
            return

        try:
            telework_day = self.sudo()
            workstation_model = self.env['office.workstation'].sudo()

            records_sudo = telework_day.search([
                ('date', '=', target_date),
            ])

            if not records_sudo:
                return

            total_available_workstations = workstation_model.search_count([
                ('active', '=', True),
            ])

            occupied_workstations = telework_day.search_count([
                ('date', '=', target_date),
                ('mode', '=', 'onsite'),
                ('state', 'in', ['confirmed', 'draft', 'pending_review']),
                ('workstation_id', '!=', False),
            ])

            sample_record = records_sudo[:1]
            if sample_record:
                date_available_for_booking = (
                    sample_record._is_date_available_for_booking(target_date)
                )
            else:
                date_available_for_booking = True

            if not date_available_for_booking:
                total_available_workstations = 0

            if occupied_workstations > total_available_workstations:
                total_color = 'red'
            elif occupied_workstations >= total_available_workstations:
                total_color = 'yellow'
            else:
                total_color = 'green'

            availability_values = {
                'total_availability': (
                    f"{occupied_workstations}/{total_available_workstations}"
                ),
                'total_status_color': total_color,
                'total_overbooked': (
                    occupied_workstations > total_available_workstations
                ),
            }

            records_sudo.with_context(
                skip_pending_review_transition=True
            ).write(availability_values)

        except Exception:
            pass

    def unlink(self):
        """Override unlink to maintain data integrity"""
        affected_data = []
        for rec in self:
            if rec.date and rec.department_id:
                affected_data.append({
                    'date': rec.date,
                    'department_id': rec.department_id.id,
                })

        result = super().unlink()

        if affected_data:
            dates_to_update = list(set(data['date'] for data in affected_data))
            affected_records = self.search([
                ('date', 'in', dates_to_update),
            ])

            for date in dates_to_update:
                date_records = affected_records.filtered(
                    lambda record: record.date == date)
                if date_records:
                    self._bulk_update_availability_for_date(date, date_records)

            if affected_records:
                affected_records._compute_availability_fields()

        return result

    @api.model
    def _cron_send_d_minus_one_reminders(self):
        """D-1 reminders removed - simplified notification system"""
        return True

    @api.model
    def _search_this_week(self, operator, value):
        """Search method for this week filter"""
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)

        if operator in ['=', '!='] and value in [True, False]:
            if (operator == '=' and value) or (operator == '!=' and not value):
                return [
                    '&',
                    ('date', '>=', monday),
                    ('date', '<=', sunday)
                ]
            else:
                return [
                    '|',
                    ('date', '<', monday),
                    ('date', '>', sunday)
                ]
        return []

    @api.model
    def _search_next_week(self, operator, value):
        """Search method for next week filter"""
        today = date.today()
        next_monday = today + timedelta(days=7-today.weekday())
        next_sunday = next_monday + timedelta(days=6)

        if operator in ['=', '!='] and value in [True, False]:
            if (operator == '=' and value) or (operator == '!=' and not value):
                return [
                    '&',
                    ('date', '>=', next_monday),
                    ('date', '<=', next_sunday)
                ]
            else:
                return [
                    '|',
                    ('date', '<', next_monday),
                    ('date', '>', next_sunday)
                ]
        return []

    @api.model
    def get_week_dates(self, week='current'):
        """Calculate start and end dates of current or next week"""
        today = date.today()

        if week == 'current':
            monday = today - timedelta(days=today.weekday())
            sunday = monday + timedelta(days=6)
        else:
            monday = today + timedelta(days=7-today.weekday())
            sunday = monday + timedelta(days=6)

        return {
            'start': monday.strftime('%Y-%m-%d'),
            'end': sunday.strftime('%Y-%m-%d')
        }

    @api.model
    def _auto_assign_workstations_internal(
            self, declarations=None, notify_reviewers=True):
        """Core logic for automatic workstation assignment."""
        TeleworkDay = self.env['hr.telework.day']

        if declarations is None:
            unassigned_declarations = TeleworkDay.search([
                ('mode', '=', 'onsite'),
                ('workstation_id', '=', False),
                ('state', 'in', ['draft', 'confirmed'])
            ])
        else:
            unassigned_declarations = declarations.filtered(
                lambda d: (
                    d.mode == 'onsite'
                    and not d.workstation_id
                    and d.state in ['draft', 'confirmed']
                )
            )

        initial_count = len(unassigned_declarations)
        if not unassigned_declarations:
            return {
                'assigned_count': 0,
                'waiting_list_count': 0,
                'initial_count': initial_count,
                'pending_records': TeleworkDay.browse(),
                'processed_records': unassigned_declarations,
            }

        assigned_count = 0
        waiting_list_count = 0

        for declaration in unassigned_declarations:
            if declaration.workstation_id:
                continue

            employee = declaration.employee_id
            if employee.primary_workstation_id:
                if self._is_workstation_available(
                        employee.primary_workstation_id, declaration.date):
                    declaration.workstation_id = (
                        employee.primary_workstation_id.id)
                    assigned_count += 1
                    if not notify_reviewers:
                        declaration.message_post(
                            body=(
                                "✅ Own workstation assigned: "
                                f"{employee.primary_workstation_id.name}"
                            )
                        )

        remaining_declarations = unassigned_declarations.filtered(
            lambda d: not d.workstation_id)

        for declaration in remaining_declarations:
            if declaration.workstation_id:
                continue

            employee = declaration.employee_id
            if employee.department_id:
                dept_workstations = self.env['office.workstation'].search([
                    ('department_id', '=', employee.department_id.id)
                ])

                for station in dept_workstations:
                    if self._is_workstation_available(
                            station, declaration.date):
                        declaration.workstation_id = station.id
                        assigned_count += 1
                        if not notify_reviewers:
                            declaration.message_post(
                                body=(
                                    "✅ Department workstation assigned: "
                                    f"{station.name}"
                                )
                            )
                        break

        remaining_declarations = unassigned_declarations.filtered(
            lambda d: not d.workstation_id)

        all_workstations = self.env['office.workstation'].search([])
        for declaration in remaining_declarations:
            if declaration.workstation_id:
                continue

            for station in all_workstations:
                if self._is_workstation_available(station, declaration.date):
                    declaration.workstation_id = station.id
                    assigned_count += 1
                    if not notify_reviewers:
                        declaration.message_post(
                            body=(
                                "✅ Available workstation assigned: "
                                f"{station.name}"
                            )
                        )
                    break

        final_unassigned = unassigned_declarations.filtered(
            lambda d: not d.workstation_id)

        for declaration in final_unassigned:
            if declaration.state != 'pending_review':
                waiting_list_count += 1
                declaration.state = 'pending_review'
                if not notify_reviewers:
                    declaration.message_post(
                        body=(
                            "⏳ On waiting list - No workstations "
                            "available. Status changed to 'Pending "
                            "Review'."
                        )
                    )

        all_affected_dates = {
            d.date for d in unassigned_declarations if d.date
        }
        if all_affected_dates:
            affected_records = TeleworkDay.search([
                ('date', 'in', list(all_affected_dates))
            ])
            affected_records._update_availability_info()
            affected_records.invalidate_recordset([
                'total_availability', 'total_status_color'
            ])

        if notify_reviewers and waiting_list_count > 0:
            TeleworkDay._notify_reviewers_pending_assignments()

        return {
            'assigned_count': assigned_count,
            'waiting_list_count': waiting_list_count,
            'initial_count': initial_count,
            'pending_records': final_unassigned,
            'processed_records': unassigned_declarations,
        }

    @api.model
    def action_auto_assign_workstations(self):
        """UI Action: reuses common automatic assignment logic."""
        result = self._auto_assign_workstations_internal()

        if result.get('initial_count', 0) == 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '❌ No Declarations',
                    'message': 'No on-site declarations without '
                               'assigned workstation',
                    'type': 'warning',
                }
            }

        assigned_count = result.get('assigned_count', 0)
        waiting_list_count = result.get('waiting_list_count', 0)

        message = (f'✅ {assigned_count} workstations assigned\n'
                   f'⏳ {waiting_list_count} on waiting list')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '🎯 Assignment Completed',
                'message': message,
                'type': 'success' if assigned_count > 0 else 'info',
            }
        }

    def _is_workstation_available(self, workstation, target_date):
        """Check if a workstation is available on a specific date"""
        occupied = self.search_count([
            ('date', '=', target_date),
            ('workstation_id', '=', workstation.id),
            ('mode', '=', 'onsite'),
            ('state', 'in', ['confirmed', 'draft', 'pending_review'])
        ])
        return occupied == 0

    @api.model
    def _notify_reviewers_pending_assignments(self):
        """Removed - simplified to Odoo notification for managers only"""
        return True

    def _notify_managers_pending_review_state(self):
        """Send Odoo notification when records go to pending review"""
        manager_group = self.env.ref(
            'hr_telework_tracking_site_capacity.group_telework_manager',
            raise_if_not_found=False,
        )
        hr_manager_group = self.env.ref(
            'hr.group_hr_manager', raise_if_not_found=False
        )

        manager_users = self.env['res.users']
        if manager_group:
            manager_users |= manager_group.users
        if hr_manager_group:
            manager_users |= hr_manager_group.users

        if not manager_users:
            return

        list_items = []
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url'
        )
        company_id = self.env.company.id

        for record in self:
            date_label = (
                format_date(self.env, record.date)
                if record.date
                else _('No date')
            )
            employee = record.employee_id.name or _('No employee')
            department = (
                record.department_id.name
                if record.department_id
                else _('No department')
            )

            # Create link to the record
            record_url = (
                f"{base_url}/web#id={record.id}&"
                f"model=hr.telework.day&view_type=form&cids={company_id}"
            )
            list_items.append(
                f'<li><a href="{record_url}">{employee} - {date_label} '
                f'({department})</a></li>'
            )

        if not list_items:
            return

        message_body = (
            '<p><strong>' +
            _('Pending review declarations:') +
            '</strong></p>'
            '<ul>' + ''.join(list_items) + '</ul>'
        )

        telework_bot = self.env.ref(
            'hr_telework_tracking_site_capacity.user_telework_bot',
            raise_if_not_found=False
        )

        if not telework_bot:
            return

        for user in manager_users:
            if not user.partner_id:
                continue

            channel_info = self.env['mail.channel'].with_user(
                telework_bot
            ).channel_get([telework_bot.partner_id.id, user.partner_id.id])
            channel = self.env['mail.channel'].browse(channel_info['id'])

            channel.with_context(
                mail_create_nosubscribe=True,
                mail_notify_force_send=False,
            ).sudo().message_post(
                body=message_body,
                author_id=telework_bot.partner_id.id,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

    def _generate_weekly_notification_message(
        self, start_label, end_label, total_days, remote_days,
        onsite_days, assigned_count, waiting_count,
        pending_review_count, employee_count
    ):
        """Generate weekly notification message with translations"""
        return (
            '<p><strong>' +
            _('Automatic schedule generated for week %s to %s') %
            (start_label, end_label) +
            '</strong></p>'
            '<ul>'
            '<li>' +
            _('%s declarations generated (%s remote, %s on-site)') %
            (total_days, remote_days, onsite_days) +
            '</li>'
            '<li>' +
            _('%s workstations assigned (%s on waiting list)') %
            (assigned_count, waiting_count) +
            '</li>'
            '<li>' +
            _('%s declarations pending review') % pending_review_count +
            '</li>'
            '<li>' +
            _('%s employees affected') % employee_count +
            '</li>'
            '</ul>'
        )

    @api.model
    def _notify_managers_weekly_generation(self, week_start, created_records,
                                           assignment_summary):
        """Send Odoo notification to managers after automatic generation"""
        if not created_records:
            return

        manager_group = self.env.ref(
            'hr_telework_tracking_site_capacity.group_telework_manager',
            raise_if_not_found=False,
        )
        hr_manager_group = self.env.ref(
            'hr.group_hr_manager', raise_if_not_found=False
        )

        manager_users = self.env['res.users']
        if manager_group:
            manager_users |= manager_group.users
        if hr_manager_group:
            manager_users |= hr_manager_group.users

        if not manager_users:
            return

        week_end = week_start + timedelta(days=4)
        week_range_end = week_start + timedelta(days=6)
        start_label = format_date(self.env, week_start)
        end_label = format_date(self.env, week_end)

        total_days = len(created_records)
        remote_days = len(
            created_records.filtered(lambda record: record.mode == 'remote')
        )
        onsite_days = len(
            created_records.filtered(lambda record: record.mode == 'onsite')
        )

        assigned_count = assignment_summary.get('assigned_count', 0)
        waiting_count = assignment_summary.get('waiting_list_count', 0)

        pending_review_count = self.search_count([
            ('date', '>=', week_start),
            ('date', '<=', week_range_end),
            ('state', '=', 'pending_review'),
            ('source', '=', 'auto_rule'),
        ])

        employees = created_records.mapped('employee_id')
        employee_count = len(employees.filtered('auto_generate_week'))

        telework_bot = self.env.ref(
            'hr_telework_tracking_site_capacity.user_telework_bot',
            raise_if_not_found=False
        )

        if not telework_bot:
            return

        for user in manager_users:
            if not user.partner_id:
                continue

            # Generate message in user's language
            ctx_self = self.with_context(lang=user.lang)
            message_body = ctx_self._generate_weekly_notification_message(
                start_label, end_label, total_days, remote_days,
                onsite_days, assigned_count, waiting_count,
                pending_review_count, employee_count
            )

            channel_info = self.env['mail.channel'].with_user(
                telework_bot
            ).channel_get([telework_bot.partner_id.id, user.partner_id.id])
            channel = self.env['mail.channel'].browse(channel_info['id'])

            channel.with_context(
                mail_create_nosubscribe=True,
                mail_notify_force_send=False,
            ).sudo().message_post(
                body=message_body,
                author_id=telework_bot.partner_id.id,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

    @api.model
    def _notify_managers_auto_confirmation(
            self, week_start, confirmed_records, unconfirmed_records,
            pending_review_records, errors):
        """Send Odoo notification to managers after auto-confirmation"""
        manager_group = self.env.ref(
            'hr_telework_tracking_site_capacity.group_telework_manager',
            raise_if_not_found=False,
        )
        hr_manager_group = self.env.ref(
            'hr.group_hr_manager', raise_if_not_found=False
        )

        manager_users = self.env['res.users']
        if manager_group:
            manager_users |= manager_group.users
        if hr_manager_group:
            manager_users |= hr_manager_group.users

        if not manager_users:
            return

        start_label = format_date(self.env, week_start)
        end_label = format_date(self.env, week_start + timedelta(days=4))

        confirmed_total = len(confirmed_records)
        confirmed_remote = len(confirmed_records.filtered(
            lambda r: r.mode == 'remote'))
        confirmed_onsite = confirmed_total - confirmed_remote

        unconfirmed_total = len(unconfirmed_records)
        pending_review_total = len(pending_review_records)
        error_count = len(errors) if errors else 0

        message_body = _(
            '<p><strong>Auto-confirmation executed for week '
            '%s to %s</strong></p>'
            '<ul>'
            '<li>%s declarations confirmed (%s remote, %s on-site)</li>'
            '<li>%s declarations pending with waiting list</li>'
            '<li>%s issues detected</li>'
            '</ul>'
        ) % (
            start_label, end_label,
            confirmed_total, confirmed_remote, confirmed_onsite,
            pending_review_total, unconfirmed_total, error_count
        )

        telework_bot = self.env.ref(
            'hr_telework_tracking_site_capacity.user_telework_bot',
            raise_if_not_found=False
        )

        if not telework_bot:
            return

        for user in manager_users:
            if not user.partner_id:
                continue

            channel_info = self.env['mail.channel'].with_user(
                telework_bot
            ).channel_get([telework_bot.partner_id.id, user.partner_id.id])
            channel = self.env['mail.channel'].browse(channel_info['id'])

            channel.with_context(
                mail_create_nosubscribe=True,
                mail_notify_force_send=False,
            ).sudo().message_post(
                body=message_body,
                author_id=telework_bot.partner_id.id,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

    @api.model
    def _notify_employees_auto_confirmation(self, week_start, week_end,
                                            confirmed_records):
        """Send email to ALL users (employees and managers) with their
        confirmed assignments for the week, including PDF report."""
        if not confirmed_records:
            return

        employees_dict = {}
        for declaration in confirmed_records:
            employee = declaration.employee_id
            if employee not in employees_dict:
                employees_dict[employee] = []
            employees_dict[employee].append(declaration)

        pdf_report_content = None
        try:
            report = self.env['ir.actions.report'].search([
                ('report_name', '=',
                 'hr_telework_tracking_site_capacity.schedule')
            ], limit=1)
            if not report:
                pass
            else:
                offices = self.env['office.location'].search([
                    ('active', '=', True)
                ])
                office_ids = offices.ids

                wizard = self.env['telework.report.wizard'].create({
                    'date_from': week_start,
                    'date_to': week_end,
                    'office_ids': [(6, 0, office_ids)],
                })

                pdf_content, pdf_type = report.sudo()._render_qweb_pdf(
                    report.id,
                    [wizard.id],
                    data={
                        'date_from': fields.Date.to_string(week_start),
                        'date_to': fields.Date.to_string(week_end),
                        'office_ids': office_ids,
                    }
                )
                pdf_report_content = base64.b64encode(pdf_content)
                wizard.unlink()
        except Exception:
            pass

        start_label = format_date(self.env, week_start)
        end_label = format_date(self.env, week_start + timedelta(days=4))

        weekday_names = {
            0: 'Monday',
            1: 'Tuesday',
            2: 'Wednesday',
            3: 'Thursday',
            4: 'Friday',
            5: 'Saturday',
            6: 'Sunday',
        }

        for employee, declarations in employees_dict.items():
            if not employee.user_id or not employee.user_id.email:
                continue

            sorted_declarations = sorted(
                declarations, key=lambda d: d.date
            )

            table_rows = []
            for decl in sorted_declarations:
                date_str = format_date(self.env, decl.date)
                weekday = weekday_names.get(
                    decl.date.weekday(), str(decl.date.weekday())
                )
                mode_str = (
                    'Telework' if decl.mode == 'remote' else 'On-site'
                )

                if decl.workstation_id:
                    full_name = decl.workstation_id.name
                    workstation_str = ''.join(
                        c for c in full_name
                        if c.isupper() or c.isdigit() or c == '-'
                    )
                    workstation_str = re.sub(r'-+', '-', workstation_str)
                    workstation_str = workstation_str.strip('-')

                    if not workstation_str:
                        workstation_str = full_name
                else:
                    workstation_str = 'Not assigned'

                bg_color = (
                    '#e8f5e9' if decl.mode == 'onsite' else '#f5f5f5'
                )

                table_rows.append(
                    f'<tr style="background-color: {bg_color};">'
                    f'<td style="padding: 10px; border: 1px solid #ddd;">'
                    f'{date_str}</td>'
                    f'<td style="padding: 10px; border: 1px solid #ddd;">'
                    f'{weekday}</td>'
                    f'<td style="padding: 10px; border: 1px solid #ddd;">'
                    f'{mode_str}</td>'
                    f'<td style="padding: 10px; border: 1px solid #ddd;">'
                    f'{workstation_str}</td>'
                    '</tr>'
                )

            assignments_table = ''.join(table_rows)

            subject = _(
                '[Telework] Your assignments for the week of %s'
            ) % start_label

            body_html = f'''
<div style="font-family: Arial, sans-serif; max-width: 800px;
            margin: 0 auto;">
  <h2 style="color: #2c3e50;">Confirmed Assignments</h2>
  <p>Hello <strong>{employee.name}</strong>,</p>
  <p>Your telework assignments for the week from
     <strong>{start_label}</strong> to <strong>{end_label}</strong>
     have been confirmed.</p>

  <h3 style="color: #34495e; margin-top: 20px;">
      Your weekly schedule:</h3>
  <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
    <thead>
      <tr style="background-color: #3498db; color: white;">
        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">
            Date</th>
        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">
            Day</th>
        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">
            Mode</th>
        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">
            Workstation</th>
      </tr>
    </thead>
    <tbody>
      {assignments_table}
    </tbody>
  </table>

  <p style="margin-top: 20px;">Attached you will find the complete
     telework assignments report.</p>

  <p style="margin-top: 30px; color: #7f8c8d; font-size: 12px;">
    If you have any questions or need to make changes, please contact your
    manager or the HR department.
  </p>
</div>
            '''

            mail_values = {
                'subject': subject,
                'body_html': body_html,
                'email_to': employee.user_id.email,
                'auto_delete': True,
            }

            mail = self.env['mail.mail'].sudo().create(mail_values)

            if pdf_report_content:
                filename = (
                    f'Telework_Assignments_'
                    f'{week_start.strftime("%Y%m%d")}.pdf'
                )
                attachment = self.env['ir.attachment'].sudo().create({
                    'name': filename,
                    'type': 'binary',
                    'datas': pdf_report_content,
                    'res_model': 'mail.mail',
                    'res_id': mail.id,
                })
                mail.attachment_ids = [(4, attachment.id)]

            mail.sudo().send()

    @api.model
    def cron_auto_confirm_weekly_declarations(self, force=True):
        """Automatically confirm system-generated declarations.

        Args:
            force (bool): If True, skip cutoff time check. Default True.
        """
        Param = self.env['ir.config_parameter'].sudo()

        def _safe_int(value, default):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        def _safe_float(value, default):
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        confirm_weekday = _safe_int(
            Param.get_param(
                'hr_telework_tracking_site_capacity.auto_confirm_weekday'
            ),
            4
        )
        confirm_time = _safe_float(
            Param.get_param(
                'hr_telework_tracking_site_capacity.auto_confirm_time'
            ),
            8.0
        )

        now = fields.Datetime.now()
        current_week_start = now.date() - timedelta(days=now.weekday())
        confirm_date = current_week_start + timedelta(days=confirm_weekday)

        confirm_hour = int(confirm_time)
        confirm_minute = int((confirm_time - confirm_hour) * 60)

        confirm_dt = datetime.combine(
            confirm_date,
            datetime.min.time()
        ).replace(
            hour=confirm_hour,
            minute=confirm_minute,
            second=0,
            microsecond=0
        )

        if not force and now < confirm_dt:
            return 0

        target_week_start = current_week_start + timedelta(days=7)
        target_week_end = target_week_start + timedelta(days=6)

        declarations = self.search([
            ('date', '>=', target_week_start),
            ('date', '<=', target_week_end),
            ('state', '=', 'draft'),
            ('source', '=', 'auto_rule'),
        ])

        if not declarations:
            all_decl = self.search([
                ('date', '>=', target_week_start),
                ('date', '<=', target_week_end),
            ])
            if all_decl:
                states = {}
                sources = {}
                for d in all_decl:
                    states[d.state] = states.get(d.state, 0) + 1
                    sources[d.source or 'none'] = (
                        sources.get(d.source or 'none', 0) + 1
                    )
            return 0

        confirmable = declarations.filtered(
            lambda rec: rec.mode == 'remote' or rec.workstation_id
        )
        confirmed_records = self.browse()
        errors = []

        for declaration in confirmable:
            try:
                declaration.action_confirm()
                confirmed_records |= declaration
            except Exception as error:
                errors.append((declaration, str(error)))

        unconfirmed_records = declarations - confirmed_records

        pending_review_records = self.search([
            ('date', '>=', target_week_start),
            ('date', '<=', target_week_end),
            ('state', '=', 'pending_review'),
            ('source', '=', 'auto_rule'),
        ])

        self._notify_managers_auto_confirmation(
            target_week_start,
            confirmed_records,
            unconfirmed_records,
            pending_review_records,
            errors
        )
        self._notify_employees_auto_confirmation(
            target_week_start,
            target_week_end,
            confirmed_records
        )

        return len(confirmed_records)
