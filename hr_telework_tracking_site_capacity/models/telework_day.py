# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import base64
import logging
import re
from datetime import date, datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_date


_logger = logging.getLogger(__name__)


class HrTeleworkDay(models.Model):
    _name = 'hr.telework.day'
    _description = 'Day Declaration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date desc, employee_id'

    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one(
        'hr.employee', required=True, index=True, tracking=True)
    user_id = fields.Many2one(
        related='employee_id.user_id', store=True, index=True)
    department_id = fields.Many2one(
        'hr.department', string='Department', required=True, index=True,
        tracking=True)
    workstation_id = fields.Many2one(
        'office.workstation', string='Workstation', index=True,
        tracking=True,
        help='Workstation assigned for this day')

    date = fields.Date(required=True, index=True, tracking=True)
    date_display = fields.Char(
        string='Date', compute='_compute_date_display', store=True)

    create_date = fields.Datetime(
        string='Creation Date', readonly=True,
        help='Date and time when the declaration was created')

    mode = fields.Selection([
        ('remote', 'Remote Work'),
        ('onsite', 'On-site'),
    ], required=True, default='onsite', tracking=True)

    mode_icon = fields.Char(
        string='Icon', compute='_compute_mode_icon', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_review', 'Pending Review'),
        ('confirmed', 'Confirmed'),
    ], default='draft', tracking=True, index=True)

    note = fields.Text()
    source = fields.Selection([
        ('self', 'Employee'),
        ('manager', 'Manager'),
        ('auto_rule', 'Automatic Rule'),
    ], default='self', tracking=True)

    overbooked = fields.Boolean(
        readonly=True, copy=False, tracking=True,
        help='Marked if confirmation exceeds capacity (flexible mode).')

    # Only keep total availability
    total_availability = fields.Char(
        string='Total Avail.',
        help='Total company availability')

    total_status_color = fields.Selection([
        ('green', 'Available'),
        ('yellow', 'Full'),
        ('red', 'Overbooked'),
    ], string='Total Color', default='green')

    total_overbooked = fields.Boolean(
        string='Total Overbooked', default=False,
        help='Total company capacity exceeded')

    office_availability = fields.Text(
        string='Availability by Office',
        compute='_compute_office_availability',
        store=False,
        help='Detailed availability information by office')

    # Fields for dynamic week filters
    is_this_week = fields.Boolean(
        string='This Week', compute='_compute_week_flags',
        search='_search_this_week', store=False)
    is_next_week = fields.Boolean(
        string='Next Week', compute='_compute_week_flags',
        search='_search_next_week', store=False)

    # Field for statistics
    percentage_telework = fields.Float(
        string='Telework Percentage',
        compute='_compute_percentage_telework',
        store=True,
        help='Telework percentage (100 if remote, 0 if on-site)')

    # Fields for conflict handling
    has_workstation_conflict = fields.Boolean(
        string='Has Workstation Conflict',
        compute='_compute_workstation_conflicts',
        store=False,
        help='True if this workstation is occupied by other declarations')

    conflicting_declaration_ids = fields.Many2many(
        'hr.telework.day',
        'hr_telework_conflict_rel',
        'declaration_id',
        'conflicting_id',
        string='Conflicting Declarations',
        compute='_compute_workstation_conflicts',
        store=False,
        help='Other declarations using the same workstation on the same date')

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
            mode_dict = dict(self._fields['mode'].selection)
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

            # Build search domain
            domain = [
                ('date', '=', rec.date),
                ('workstation_id', '=', rec.workstation_id.id),
                ('mode', '=', 'onsite'),
                ('state', 'in', ['confirmed', 'draft', 'pending_review']),
            ]

            # Only exclude current record if it has a real ID (not NewId)
            if rec.id and str(rec.id).isdigit():
                domain.append(('id', '!=', rec.id))

            # Search for conflicting records
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

            # Get all active offices
            offices = Office.search([
                ('active', '=', True)
            ], order='name')

            office_info = []
            total_occupied = 0
            total_workstations = 0

            for office in offices:
                # Count total workstations in this office
                office_workstations = Workstation.search_count([
                    ('office_id', '=', office.id),
                    ('active', '=', True)
                ])

                # Count occupied workstations for this date
                occupied = TeleworkDay.search_count([
                    ('date', '=', rec.date),
                    ('mode', '=', 'onsite'),
                    ('state', 'in', ['confirmed', 'draft', 'pending_review']),
                    ('workstation_id.office_id', '=', office.id)
                ])

                # Add to totals
                total_occupied += occupied
                total_workstations += office_workstations

                # Format office information with full names
                if office_workstations > 0:
                    percentage = round((occupied / office_workstations) * 100)
                    # Determine color based on occupancy
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
                # Calculate total percentage
                if total_workstations > 0:
                    total_percentage = round(
                        (total_occupied / total_workstations) * 100
                    )
                else:
                    total_percentage = 0

                # Generate clean table for better presentation
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

                # Determine totals styling
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
                        <td><strong>Total</strong></td>
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
                            <th>Office</th>
                            <th>Occupied</th>
                            <th>Status</th>
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
                    '<p class="text-muted">No offices configured</p>'
                )

    @api.depends('date')
    def _compute_date_display(self):
        """Compute date display with weekday name"""
        weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
                    'Saturday', 'Sunday']
        for rec in self:
            if rec.date:
                weekday = weekdays[rec.date.weekday()]
                rec.date_display = f"{weekday} {rec.date.strftime('%d/%m/%Y')}"
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
        # Calculate Monday of this week
        monday_this_week = today - timedelta(days=today.weekday())
        # Calculate Sunday of this week
        sunday_this_week = monday_this_week + timedelta(days=6)
        # Calculate Monday of next week
        monday_next_week = monday_this_week + timedelta(days=7)
        # Calculate Sunday of next week
        sunday_next_week = monday_next_week + timedelta(days=6)

        for rec in self:
            if rec.date:
                # This week
                rec.is_this_week = (
                    monday_this_week <= rec.date <= sunday_this_week)
                # Next week
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

        # Group by date for efficient processing
        date_groups = {}
        for rec in self:
            if rec.date:
                if rec.date not in date_groups:
                    date_groups[rec.date] = []
                date_groups[rec.date].append(rec)

        # Process each date
        for date, records in date_groups.items():
            self._bulk_update_availability_for_date(date, records)

    def force_refresh_availability(self):
        """Force refresh of availability data for current records"""
        self._update_availability_info()

    def action_confirm(self):
        # Only managers can confirm declarations
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

        # Check for workstation conflicts before confirming
        for rec in self:
            if rec.has_workstation_conflict:
                raise UserError(
                    _('Cannot confirm declaration: the workstation is '
                      'already occupied by another declaration on the '
                      'same date.')
                )

        # Check configuration policy
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

            # Refresh view to update computed fields
            self._refresh_capacity_display()
            # Force complete recalculation
            self._compute_availability_fields()

            if over:
                rec._notify_overbooked()
                # Show prominent visual warning but DO NOT return action
                # to allow the view to refresh normally
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

        # Force recalculation of all computed fields in the view
        self.invalidate_recordset()

        # Return True to allow normal view refresh
        return True

    def _refresh_capacity_display(self):
        """Update capacity info for related records efficiently"""
        for rec in self:
            # Find all records from the same department and date
            related_records = self.search([
                ('date', '=', rec.date),
                ('department_id', '=', rec.department_id.id),
            ])
            # Update only the fields we really need
            for record in related_records:
                record._update_availability_info()

            # Also update availability for other departments
            # so they see up-to-date data, but only capacity_info
            other_records = self.search([
                ('date', '=', rec.date),
                ('department_id', '!=', rec.department_id.id),
            ])
            other_records._update_availability_info()

    def action_set_draft(self):
        # Only managers can change state back to draft
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
            # Refresh view when changing to draft as well
            rec._refresh_capacity_display()
            # Force complete recalculation
            rec._compute_availability_fields()

    def _check_cutoff_on_confirm(self):
        """Check if confirmation is allowed according to cutoff day and time"""
        # Get cutoff day and time configuration
        Param = self.env['ir.config_parameter'].sudo()
        cutoff_weekday = int(Param.get_param(
            'hr_telework_tracking_site_capacity.cutoff_weekday', '4'
        ))  # Friday
        cutoff_time = float(Param.get_param(
            'hr_telework_tracking_site_capacity.cutoff_time', '18.0'))  # 18:00

        # Convert to hours and minutes
        cutoff_hour = int(cutoff_time)
        cutoff_minute = int((cutoff_time % 1) * 60)

        now = datetime.now()

        for rec in self:
            # If the declaration is for today, it can always be confirmed
            if rec.date == now.date():
                continue

            # If it is for a past date, it cannot be confirmed
            if rec.date < now.date():
                raise UserError(
                    f'Cannot confirm a declaration for a past date '
                    f'({rec.date_display})')

            # Check if we are after the cutoff day/time of this week
            days_since_monday = now.weekday()  # 0=Monday, 6=Sunday

            # Calculate how many days until cutoff day
            days_to_cutoff = cutoff_weekday - days_since_monday
            if days_to_cutoff < 0:
                days_to_cutoff += 7  # If already passed this week, go to next

            # Create cutoff datetime
            cutoff_dt = now.replace(
                hour=cutoff_hour,
                minute=cutoff_minute,
                second=0,
                microsecond=0
            ) + timedelta(days=days_to_cutoff)

            # If we have passed the cutoff day/time and the target date is
            # next week, check permissions
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
        # Notification already shown in action_confirm via bus.bus
        # No email sent, only visual warning
        pass

    def _get_department_capacity(self, date, department):
        """Get department capacity from office workstations.

        Searches for total capacity of workstations available
        for the department in all offices.
        Only counts stations available for booking on the given date.
        If no stations are configured, uses the global default capacity.
        """
        # Check if the date is available for bookings
        if not self._is_date_available_for_booking(date):
            # If the date is not available for new bookings,
            # capacity is 0 for new assignments
            return 0

        # Search for all active offices
        offices = self.env['office.location'].search([('active', '=', True)])
        total_capacity = 0

        for office in offices:
            # Count active workstations in this office
            # If department is specific, filter by department
            # Otherwise, count all stations
            workstations = self.env['office.workstation'].search([
                ('office_id', '=', office.id),
                ('active', '=', True)
            ])

            if department:
                # Filter by department if specified
                dept_workstations = workstations.filtered(
                    lambda w: w.department_id == department)
                if dept_workstations:
                    total_capacity += len(dept_workstations)
                else:
                    # If there are no department-specific stations,
                    # use stations without assigned department
                    generic_workstations = workstations.filtered(
                        lambda w: not w.department_id)
                    total_capacity += len(generic_workstations)
            else:
                # If no department, count all stations
                total_capacity += len(workstations)

        # If no stations configured, use global default capacity
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
            # Get cutoff time configuration
            config_param = self.env['ir.config_parameter'].sudo()
            cutoff_weekday_param = config_param.get_param(
                'hr_telework_tracking_site_capacity.cutoff_weekday')
            cutoff_time_param = config_param.get_param(
                'hr_telework_tracking_site_capacity.cutoff_time')

            if not cutoff_weekday_param:
                return True  # If no configuration, always available

            from datetime import datetime, timedelta

            cutoff_weekday = int(cutoff_weekday_param)  # 0=Monday, 6=Sunday
            cutoff_time = float(cutoff_time_param or 18.0)

            # Convert target_date to datetime if necessary
            if isinstance(target_date, str):
                target_date = fields.Date.from_string(target_date)

            # Get Monday of target_date week
            days_since_monday = target_date.weekday()
            monday_of_target_week = target_date - timedelta(
                days=days_since_monday)

            # Calculate cutoff day of that week
            cutoff_date = monday_of_target_week + timedelta(
                days=cutoff_weekday)

            # Create datetime of cutoff moment
            cutoff_hour = int(cutoff_time)
            cutoff_minute = int((cutoff_time - cutoff_hour) * 60)

            cutoff_datetime = datetime.combine(
                cutoff_date,
                datetime.min.time().replace(
                    hour=cutoff_hour,
                    minute=cutoff_minute
                ))

            # Date is available if we haven't passed the cutoff moment
            now = datetime.now()
            return now <= cutoff_datetime

        except Exception:
            # En caso de error, permitir la reserva
            return True

    def debug_capacity_calculation(self):
        """Método de debug para verificar cálculo de capacidad"""
        for rec in self:
            print(f"\n=== Debug Capacidad para {rec.date} ===")

            # Contar estaciones totales activas
            total_workstations = self.env['office.workstation'].search_count([
                ('active', '=', True)
            ])
            print(f"Total estaciones activas: {total_workstations}")

            # Contar estaciones ocupadas en esta fecha
            occupied_workstations = self.search_count([
                ('date', '=', rec.date),
                ('mode', '=', 'onsite'),
                ('state', 'in', ['confirmed', 'draft', 'pending_review']),
                ('workstation_id', '!=', False)
            ])
            print(
                f"Estaciones ocupadas en {rec.date}: "
                f"{occupied_workstations}"
            )

            # Verificar disponibilidad de fecha
            available = rec._is_date_available_for_booking(rec.date)
            print(f"Fecha disponible para reservas: {available}")

            # Mostrar cálculo final
            if not available:
                print("Capacidad mostrada: 0 (fecha no disponible)")
            else:
                print(
                    f"Capacidad mostrada: {occupied_workstations}/"
                    f"{total_workstations}"
                )

            # Mostrar declaraciones específicas de la fecha
            date_declarations = self.search([
                ('date', '=', rec.date),
                ('mode', '=', 'onsite')
            ])
            print(f"Declaraciones presenciales en {rec.date}:")
            for decl in date_declarations:
                ws_name = (
                    decl.workstation_id.name
                    if decl.workstation_id
                    else "Sin puesto"
                )
                print(f"  - {decl.employee_id.name}: {ws_name} ({decl.state})")

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
        # count es existentes; si este confirma, sería count+1
        return (count + 1) > cap

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to invalidate computed fields of related records"""
        # Ensure department_id is set for all records
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        for vals in vals_list:
            if 'employee_id' in vals and 'department_id' not in vals:
                employee = self.env['hr.employee'].browse(vals['employee_id'])
                if employee.department_id:
                    vals['department_id'] = employee.department_id.id

        records = super().create(vals_list)

        # Avisar a gestores si se crea en pendiente de revisión
        newly_pending = self.browse()
        for vals, record in zip(vals_list, records):
            is_pending = vals.get('state') == 'pending_review'
            if is_pending and record.state == 'pending_review':
                newly_pending |= record

        if newly_pending:
            newly_pending._notify_managers_pending_review_state()

        # Actualizar disponibilidad para las fechas de los nuevos registros
        dates_affected = set(rec.date for rec in records if rec.date)
        if dates_affected:
            for date in dates_affected:
                date_records = self.search([('date', '=', date)])
                if date_records:
                    self._bulk_update_availability_for_date(date, date_records)

        return records

    def write(self, vals):
        """Override write to maintain data integrity and track user changes"""
    # Guardar info previa para actualizar registros relacionados
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

        # Registrar modificación en bitácora si el usuario no es gestor
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

        # Si no es gestor y está modificando declaraciones, registrar
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

        # Campos que afectan la disponibilidad y requieren recálculo
        critical_fields = [
            'date', 'employee_id', 'workstation_id', 'mode', 'state'
        ]

        if any(field in vals for field in critical_fields):
            # Invalidar campos de conflictos para recálculo
            if 'workstation_id' in vals or 'date' in vals or 'state' in vals:
                # Invalidar campos de conflicto para este registro
                self.invalidate_recordset(['has_workstation_conflict',
                                          'conflicting_declaration_ids'])

                # También invalidar para otros registros afectados
                if 'workstation_id' in vals or 'date' in vals:
                    # Buscar otros registros con la misma estación/fecha
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

            # Actualizar disponibilidad después de cambios importantes
            availability_fields = ['workstation_id', 'state', 'date', 'mode']
            if any(field in vals for field in availability_fields):
                self._update_related_availability_data(old_data, vals)

        return result

    def _compute_availability_fields(self):
        """Fuerza el recálculo solo de disponibilidad total - optimizado"""
        # Obtener todas las fechas afectadas
        dates_affected = set(rec.date for rec in self if rec.date)

        if dates_affected:
            # Buscar todos los registros de esas fechas
            all_affected = self.search([
                ('date', 'in', list(dates_affected))
            ])

            if all_affected:
                # Solo invalidar campos esenciales
                all_affected.invalidate_recordset([
                    'total_availability',
                    'total_status_color',
                    'total_overbooked',
                ])

                # Actualizar disponibilidad usando el helper optimizado
                all_affected._update_availability_info()

    def _update_related_availability_data(self, old_data, new_vals):
        """Update availability data for all related records after changes"""
        dates_to_update = set()
        departments_to_update = set()

        # Recopilar todas las fechas y departamentos afectados
        for i, rec in enumerate(self):
            old_info = old_data[i]

            # Fechas afectadas: la antigua y la nueva
            if old_info['old_date']:
                dates_to_update.add(old_info['old_date'])
            if rec.date:
                dates_to_update.add(rec.date)

            # Departamentos afectados: el antiguo y el nuevo
            if old_info['old_department_id']:
                departments_to_update.add(old_info['old_department_id'])
            if rec.department_id:
                departments_to_update.add(rec.department_id.id)

        # Actualizar todos los registros que pueden verse afectados
        if dates_to_update:
            affected_records = self.search([
                ('date', 'in', list(dates_to_update)),
            ])

            # Actualizar en lotes por fecha para optimizar
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

            # Buscar registros de la fecha sin restricciones de acceso
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

        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(
                "Error updating availability for date %s: %s",
                target_date,
                e,
            )

    def unlink(self):
        """Override unlink to maintain data integrity"""
        # Recopilar información de los registros que se van a eliminar
        affected_data = []
        for rec in self:
            if rec.date and rec.department_id:
                affected_data.append({
                    'date': rec.date,
                    'department_id': rec.department_id.id,
                })

        result = super().unlink()

        # Actualizar registros relacionados después de la eliminación
        if affected_data:
            dates_to_update = list(set(data['date'] for data in affected_data))
            affected_records = self.search([
                ('date', 'in', dates_to_update),
            ])

            # Actualizar por fecha
            for date in dates_to_update:
                date_records = affected_records.filtered(
                    lambda record: record.date == date)
                if date_records:
                    self._bulk_update_availability_for_date(date, date_records)

            # Forzar recálculo para registros afectados
            if affected_records:
                affected_records._compute_availability_fields()

        return result

    @api.model
    def _cron_send_d_minus_one_reminders(self):
        """D-1 reminders removed - simplified notification system"""
        # Feature removed to simplify notifications
        return True

    @api.model
    def _search_this_week(self, operator, value):
        """Search method for this week filter"""
        today = date.today()
        # Calcular lunes de esta semana
        monday = today - timedelta(days=today.weekday())
        # Calcular domingo de esta semana
        sunday = monday + timedelta(days=6)

        # Si se busca is_this_week = True
        if operator in ['=', '!='] and value in [True, False]:
            if (operator == '=' and value) or (operator == '!=' and not value):
                # Queremos registros dentro de esta semana
                return [
                    '&',
                    ('date', '>=', monday),
                    ('date', '<=', sunday)
                ]
            else:
                # Queremos registros fuera de esta semana
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
        # Calcular lunes de la próxima semana
        next_monday = today + timedelta(days=7-today.weekday())
        # Calcular domingo de la próxima semana
        next_sunday = next_monday + timedelta(days=6)

        # Si se busca is_next_week = True
        if operator in ['=', '!='] and value in [True, False]:
            if (operator == '=' and value) or (operator == '!=' and not value):
                # Queremos registros dentro de la próxima semana
                return [
                    '&',
                    ('date', '>=', next_monday),
                    ('date', '<=', next_sunday)
                ]
            else:
                # Queremos registros fuera de la próxima semana
                return [
                    '|',
                    ('date', '<', next_monday),
                    ('date', '>', next_sunday)
                ]
        return []

    @api.model
    def get_week_dates(self, week='current'):
        """Calcula fechas de inicio y fin de la semana actual o siguiente"""
        today = date.today()

        if week == 'current':
            # Lunes de esta semana
            monday = today - timedelta(days=today.weekday())
            # Domingo de esta semana
            sunday = monday + timedelta(days=6)
        else:  # week == 'next'
            # Lunes de la próxima semana
            monday = today + timedelta(days=7-today.weekday())
            # Domingo de la próxima semana
            sunday = monday + timedelta(days=6)

        return {
            'start': monday.strftime('%Y-%m-%d'),
            'end': sunday.strftime('%Y-%m-%d')
        }

    # Note: Custom search methods for week_filter removed as the feature
    # was discontinued to resolve view validation issues.

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

        # FASE 1: Asignar puestos preferidos (prioridad máxima)
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
                    # Solo notificar si no es generación automática
                    if not notify_reviewers:
                        declaration.message_post(
                            body=(
                                "✅ Puesto propio asignado: "
                                f"{employee.primary_workstation_id.name}"
                            )
                        )

        # FASE 2: Asignar puestos del departamento
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
                        # Solo notificar si no es generación automática
                        if not notify_reviewers:
                            declaration.message_post(
                                body=(
                                    "✅ Puesto del departamento asignado: "
                                    f"{station.name}"
                                )
                            )
                        break

        # FASE 3: Asignar cualquier puesto libre
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
                    # Solo notificar si no es generación automática
                    if not notify_reviewers:
                        declaration.message_post(
                            body=(
                                "✅ Puesto libre asignado: "
                                f"{station.name}"
                            )
                        )
                    break

        # FASE 4: Lista de espera para declaraciones sin asignar
        final_unassigned = unassigned_declarations.filtered(
            lambda d: not d.workstation_id)

        for declaration in final_unassigned:
            if declaration.state != 'pending_review':
                waiting_list_count += 1
                declaration.state = 'pending_review'
                # Solo notificar si no es generación automática
                if not notify_reviewers:
                    declaration.message_post(
                        body=(
                            "⏳ En lista de espera - No hay puestos "
                            "disponibles. Estado cambiado a 'Pendiente de "
                            "Revisión'."
                        )
                    )

        # Actualizar información de disponibilidad para registros afectados
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
        """Acción UI: reutiliza la lógica común de asignación automática."""
        result = self._auto_assign_workstations_internal()

        if result.get('initial_count', 0) == 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '❌ Sin Declaraciones',
                    'message': 'No hay declaraciones presenciales sin '
                               'puesto asignado',
                    'type': 'warning',
                }
            }

        assigned_count = result.get('assigned_count', 0)
        waiting_list_count = result.get('waiting_list_count', 0)

        message = (f'✅ {assigned_count} puestos asignados\n'
                   f'⏳ {waiting_list_count} en lista de espera')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '🎯 Asignación Completada',
                'message': message,
                'type': 'success' if assigned_count > 0 else 'info',
            }
        }

    def _is_workstation_available(self, workstation, target_date):
        """Verifica si un puesto está disponible en una fecha específica"""
        occupied = self.search_count([
            ('date', '=', target_date),
            ('workstation_id', '=', workstation.id),
            ('mode', '=', 'onsite'),
            # Considerar cualquier estado que tenga puesto asignado
            ('state', 'in', ['confirmed', 'draft', 'pending_review'])
        ])
        return occupied == 0

    @api.model
    def _notify_reviewers_pending_assignments(self):
        """Removed - simplified to Odoo notification for managers only"""
        # Feature removed - managers get Odoo notification instead
        return True

    def _notify_managers_pending_review_state(self):
        """Send Odoo notification when records go to pending review"""
        # Get managers with telework or HR permissions
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

        # Build message
        list_items = []
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
            list_items.append(
                f"<li>{employee} - {date_label} ({department})</li>"
            )

        if not list_items:
            return

        message_body = _(
            '<p><strong>Pending review declarations:</strong></p>'
            '<ul>%s</ul>'
        ) % ''.join(list_items)

        # Get Telework Manager bot user
        telework_bot = self.env.ref(
            'hr_telework_tracking_site_capacity.user_telework_bot',
            raise_if_not_found=False
        )

        if not telework_bot:
            _logger.warning(
                'Telework Manager bot not found, '
                'notifications will not be sent'
            )
            return

        # Post message to managers' inbox (internal notification only)
        # Send message to each manager via direct channel (like OdooBot)
        for user in manager_users:
            if not user.partner_id:
                continue

            # Get or create direct channel between bot and manager
            channel_info = self.env['mail.channel'].with_user(
                telework_bot
            ).channel_get([telework_bot.partner_id.id, user.partner_id.id])
            channel = self.env['mail.channel'].browse(channel_info['id'])

            # Post message without sending email (internal only)
            channel.with_context(
                mail_create_nosubscribe=True,
                mail_notify_force_send=False,
            ).sudo().message_post(
                body=message_body,
                author_id=telework_bot.partner_id.id,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

        _logger.info(
            'Notification sent to %d managers about %d pending reviews',
            len(manager_users),
            len(self)
        )

    @api.model
    def _notify_managers_weekly_generation(self, week_start, created_records,
                                           assignment_summary):
        """Send Odoo notification to managers after automatic generation"""
        if not created_records:
            return

        # Get managers with telework or HR permissions
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

        # Count only employees with auto_generate_week enabled
        employees = created_records.mapped('employee_id')
        employee_count = len(employees.filtered('auto_generate_week'))

        message_body = _(
            '<p><strong>Automatic schedule generated for week '
            '%s to %s</strong></p>'
            '<ul>'
            '<li>%s declarations generated (%s remote, %s on-site)</li>'
            '<li>%s workstations assigned</li>'
            '<li>%s declarations pending review</li>'
            '<li>%s employees affected</li>'
            '</ul>'
        ) % (
            start_label, end_label,
            total_days, remote_days, onsite_days,
            assigned_count, waiting_count, pending_review_count,
            employee_count
        )

        # Get Telework Manager bot user
        telework_bot = self.env.ref(
            'hr_telework_tracking_site_capacity.user_telework_bot',
            raise_if_not_found=False
        )

        if not telework_bot:
            _logger.warning(
                'Telework Manager bot not found, '
                'notifications will not be sent'
            )
            return

        # Post message to managers' inbox (internal notification only)
        # Send message to each manager via direct channel (like OdooBot)
        for user in manager_users:
            if not user.partner_id:
                continue

            # Get or create direct channel between bot and manager
            channel_info = self.env['mail.channel'].with_user(
                telework_bot
            ).channel_get([telework_bot.partner_id.id, user.partner_id.id])
            channel = self.env['mail.channel'].browse(channel_info['id'])

            # Post message without sending email (internal only)
            channel.with_context(
                mail_create_nosubscribe=True,
                mail_notify_force_send=False,
            ).sudo().message_post(
                body=message_body,
                author_id=telework_bot.partner_id.id,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

        _logger.info(
            'Notification sent to %d managers about weekly generation',
            len(manager_users)
        )

    @api.model
    def _notify_managers_auto_confirmation(
            self, week_start, confirmed_records, unconfirmed_records,
            pending_review_records, errors):
        """Send Odoo notification to managers after auto-confirmation"""
        # Get managers with telework or HR permissions
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

        # Get Telework Manager bot user
        telework_bot = self.env.ref(
            'hr_telework_tracking_site_capacity.user_telework_bot',
            raise_if_not_found=False
        )

        if not telework_bot:
            _logger.warning(
                'Telework Manager bot not found, '
                'notifications will not be sent'
            )
            return

        # Post message to managers' inbox (internal notification only)
        # Send message to each manager via direct channel (like OdooBot)
        for user in manager_users:
            if not user.partner_id:
                continue

            # Get or create direct channel between bot and manager
            channel_info = self.env['mail.channel'].with_user(
                telework_bot
            ).channel_get([telework_bot.partner_id.id, user.partner_id.id])
            channel = self.env['mail.channel'].browse(channel_info['id'])

            # Post message without sending email (internal only)
            channel.with_context(
                mail_create_nosubscribe=True,
                mail_notify_force_send=False,
            ).sudo().message_post(
                body=message_body,
                author_id=telework_bot.partner_id.id,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

        _logger.info(
            'Notification sent to %d managers about auto-confirmation',
            len(manager_users)
        )

    @api.model
    def _notify_employees_auto_confirmation(self, week_start, week_end,
                                            confirmed_records):
        """Send email to ALL users (employees and managers) with their
        confirmed assignments for the week, including PDF report."""
        if not confirmed_records:
            return

        # Group declarations by employee
        employees_dict = {}
        for declaration in confirmed_records:
            employee = declaration.employee_id
            if employee not in employees_dict:
                employees_dict[employee] = []
            employees_dict[employee].append(declaration)

        # Generate single unified PDF report for all employees
        pdf_report_content = None
        try:
            # Find report by report_name instead of XML ID for reliability
            _logger.info(
                'Searching for telework report with report_name: '
                'hr_telework_tracking_site_capacity.schedule'
            )
            report = self.env['ir.actions.report'].search([
                ('report_name', '=',
                 'hr_telework_tracking_site_capacity.schedule')
            ], limit=1)
            _logger.info(
                'Report search result: %s (ID: %s)',
                report.name if report else 'NOT FOUND',
                report.id if report else 'N/A'
            )
            if not report:
                _logger.error(
                    'Telework report not found! '
                    'Please update the module.'
                )
            else:
                # Get all active offices
                offices = self.env['office.location'].search([
                    ('active', '=', True)
                ])
                office_ids = offices.ids
                _logger.info(
                    'Found %s active offices: %s',
                    len(offices), offices.mapped('name')
                )

                # Create temporary wizard to generate the report
                wizard = self.env['telework.report.wizard'].create({
                    'date_from': week_start,
                    'date_to': week_end,
                    'office_ids': [(6, 0, office_ids)],
                })
                _logger.info(
                    'Created wizard ID: %s for date range %s to %s '
                    'with %s offices',
                    wizard.id, week_start, week_end, len(office_ids)
                )
                _logger.info(
                    'About to render PDF with report ID: %s, wizard ID: %s',
                    report.id, wizard.id
                )
                # Use _render_qweb_pdf with the report's model name
                # to avoid issues with mis_builder override
                pdf_content, pdf_type = report.sudo()._render_qweb_pdf(
                    report.id,
                    [wizard.id],
                    data={
                        'date_from': fields.Date.to_string(week_start),
                        'date_to': fields.Date.to_string(week_end),
                        'office_ids': office_ids,
                    }
                )
                _logger.info(
                    'PDF rendered successfully, size: %s bytes',
                    len(pdf_content) if pdf_content else 0
                )
                pdf_report_content = base64.b64encode(pdf_content)
                wizard.unlink()
        except Exception as error:
            _logger.exception(
                'Error generating unified telework report: %s',
                error
            )

        # Send email to each employee
        start_label = format_date(self.env, week_start)
        end_label = format_date(self.env, week_start + timedelta(days=4))

        # Weekday names
        weekday_names = {
            0: 'Monday',
            1: 'Tuesday',
            2: 'Wednesday',
            3: 'Thursday',
            4: 'Friday',
            5: 'Sábado',
            6: 'Domingo',
        }

        for employee, declarations in employees_dict.items():
            if not employee.user_id or not employee.user_id.email:
                continue

            # Ordenar declaraciones por fecha
            sorted_declarations = sorted(
                declarations, key=lambda d: d.date
            )

            # Construir tabla HTML de asignaciones
            table_rows = []
            for decl in sorted_declarations:
                date_str = format_date(self.env, decl.date)
                weekday = weekday_names.get(
                    decl.date.weekday(), str(decl.date.weekday())
                )
                mode_str = (
                    'Teletrabajo' if decl.mode == 'remote' else 'Presencial'
                )

                # Apply same logic as PDF report - extract only uppercase
                # letters and digits
                # Example: Moval1-001 -> M1-001
                if decl.workstation_id:
                    full_name = decl.workstation_id.name
                    # Extract only uppercase letters, digits, and hyphens
                    workstation_str = ''.join(
                        c for c in full_name
                        if c.isupper() or c.isdigit() or c == '-'
                    )
                    # Clean up multiple consecutive hyphens
                    workstation_str = re.sub(r'-+', '-', workstation_str)
                    # Remove leading/trailing hyphens
                    workstation_str = workstation_str.strip('-')

                    if not workstation_str:
                        workstation_str = full_name
                else:
                    workstation_str = 'Not assigned'

                # Background color according to mode
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

            # Preparar valores para el correo
            subject = _(
                '[Teletrabajo] Tus asignaciones para la semana del %s'
            ) % start_label

            body_html = f'''
<div style="font-family: Arial, sans-serif; max-width: 800px;
            margin: 0 auto;">
  <h2 style="color: #2c3e50;">Asignaciones Confirmadas</h2>
  <p>Hola <strong>{employee.name}</strong>,</p>
  <p>Se han confirmado tus asignaciones de teletrabajo para la semana del
     <strong>{start_label}</strong> al <strong>{end_label}</strong>.</p>

  <h3 style="color: #34495e; margin-top: 20px;">
      Tu planificación semanal:</h3>
  <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
    <thead>
      <tr style="background-color: #3498db; color: white;">
        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">
            Fecha</th>
        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">
            Día</th>
        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">
            Modo</th>
        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">
            Puesto</th>
      </tr>
    </thead>
    <tbody>
      {assignments_table}
    </tbody>
  </table>

  <p style="margin-top: 20px;">Adjunto encontrarás el informe completo de
     asignaciones de teletrabajo.</p>

  <p style="margin-top: 30px; color: #7f8c8d; font-size: 12px;">
    Si tienes alguna duda o necesitas realizar cambios, contacta con tu
    responsable o el departamento de RRHH.
  </p>
</div>
            '''

            # Crear y enviar correo
            mail_values = {
                'subject': subject,
                'body_html': body_html,
                'email_to': employee.user_id.email,
                'auto_delete': True,
            }

            mail = self.env['mail.mail'].sudo().create(mail_values)

            # Attach unified PDF report if generated successfully
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
                _logger.info(
                    'PDF attachment created for %s: %s',
                    employee.name, filename
                )
            else:
                _logger.warning(
                    'No PDF content to attach for %s',
                    employee.name
                )

            mail.sudo().send()

            _logger.info(
                'Assignment email sent to %s (%s) with %d attachments',
                employee.name,
                employee.user_id.email,
                len(mail.attachment_ids)
            )

    @api.model
    def cron_auto_confirm_weekly_declarations(self, force=True):
        """Automatically confirm system-generated declarations.

        Args:
            force (bool): If True, skip cutoff time check. Default True.
        """
        _logger.info("=== AUTO-CONFIRM CRON START ===")
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

        _logger.info(
            "Auto-confirm config: weekday=%s (0=Mon), time=%.2f",
            confirm_weekday, confirm_time
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

        _logger.info(
            "Current time: %s, Confirm time: %s, Force: %s",
            now, confirm_dt, force
        )

        if not force and now < confirm_dt:
            _logger.info(
                'Auto-confirmation SKIPPED. Current time %s is before '
                'configured time %s. Use force=True to override.',
                now,
                confirm_dt
            )
            return 0

        if force:
            _logger.info("Force mode enabled - skipping cutoff check")

        target_week_start = current_week_start + timedelta(days=7)
        target_week_end = target_week_start + timedelta(days=6)

        _logger.info(
            "Target week: %s to %s", target_week_start, target_week_end
        )

        declarations = self.search([
            ('date', '>=', target_week_start),
            ('date', '<=', target_week_end),
            ('state', '=', 'draft'),
            ('source', '=', 'auto_rule'),
        ])

        _logger.info(
            "Found %d draft declarations with source='auto_rule'",
            len(declarations)
        )

        if not declarations:
            _logger.info(
                'Auto-confirmation: NO draft declarations found for week %s. '
                'Checking if any declarations exist...',
                target_week_start
            )
            # Debug: check what declarations exist
            all_decl = self.search([
                ('date', '>=', target_week_start),
                ('date', '<=', target_week_end),
            ])
            _logger.info(
                "Total declarations for target week: %d", len(all_decl)
            )
            if all_decl:
                states = {}
                sources = {}
                for d in all_decl:
                    states[d.state] = states.get(d.state, 0) + 1
                    sources[d.source or 'none'] = (
                        sources.get(d.source or 'none', 0) + 1
                    )
                _logger.info("States breakdown: %s", states)
                _logger.info("Sources breakdown: %s", sources)
            return 0

        confirmable = declarations.filtered(
            lambda rec: rec.mode == 'remote' or rec.workstation_id
        )

        _logger.info(
            "Confirmable declarations: %d (remote or with workstation)",
            len(confirmable)
        )

        confirmed_records = self.browse()
        errors = []

        for declaration in confirmable:
            try:
                declaration.action_confirm()
                confirmed_records |= declaration
                _logger.info(
                    "✓ Confirmed: %s - %s (%s)",
                    declaration.employee_id.name,
                    declaration.date,
                    declaration.mode
                )
            except Exception as error:
                errors.append((declaration, str(error)))
                _logger.error(
                    '✗ Error confirming %s (%s): %s',
                    declaration.employee_id.name,
                    declaration.date,
                    error
                )

        unconfirmed_records = declarations - confirmed_records

        pending_review_records = self.search([
            ('date', '>=', target_week_start),
            ('date', '<=', target_week_end),
            ('state', '=', 'pending_review'),
            ('source', '=', 'auto_rule'),
        ])

        # Notificar a gestores
        self._notify_managers_auto_confirmation(
            target_week_start,
            confirmed_records,
            unconfirmed_records,
            pending_review_records,
            errors
        )

        # Notify employees with their assignments
        self._notify_employees_auto_confirmation(
            target_week_start,
            target_week_end,
            confirmed_records
        )

        _logger.info(
            '=== AUTO-CONFIRM COMPLETED === Week %s - %s. '
            'Confirmed: %d, Unconfirmed: %d, Errors: %d',
            target_week_start,
            target_week_end,
            len(confirmed_records),
            len(unconfirmed_records),
            len(errors)
        )

        return len(confirmed_records)
