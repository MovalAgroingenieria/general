# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models, _


class OfficeWorkstation(models.Model):
    _name = 'office.workstation'
    _description = 'Office Workstation'
    _order = 'office_id, name'

    name = fields.Char(string='Workstation Name', required=True)
    office_id = fields.Many2one(
        'office.location', string='Office', required=True, ondelete='cascade')
    department_id = fields.Many2one(
        'hr.department', string='Assigned Department',
        help='Department this workstation belongs to (optional)')

    # Related fields
    office_name = fields.Char(
        related='office_id.name', string='Office Name',
        readonly=True, store=True)

    active = fields.Boolean(default=True)

    # Computed fields for context-based information
    is_occupied = fields.Boolean(
        string='Occupied', compute='_compute_occupation_status',
        help='Whether this workstation is occupied on the context date')
    occupation_status = fields.Char(
        string='Status', compute='_compute_occupation_status',
        help='Occupation status for the context date')

    @api.depends_context('date_context')
    def _compute_occupation_status(self):
        """Compute occupation status based on context date"""
        context_date = self.env.context.get('date_context')

        if not context_date:
            for record in self:
                record.is_occupied = False
                record.occupation_status = 'Unknown'
            return

        for record in self:
            # Check if workstation is occupied on context date
            occupied_count = self.env['hr.telework.day'].search_count([
                ('date', '=', context_date),
                ('mode', '=', 'onsite'),
                ('workstation_id', '=', record.id),
                ('state', 'in', ['confirmed', 'draft'])
            ])

            record.is_occupied = occupied_count > 0
            if occupied_count > 0:
                record.occupation_status = 'OCCUPIED'
            else:
                record.occupation_status = 'Available'

    def name_get(self):
        """Display full name with office, mark occupied workstations in red"""
        result = []
        context_date = self.env.context.get('date_context')

        # Get occupied workstations for the context date if provided
        occupied_ids = set()
        if context_date:
            occupied_declarations = self.env['hr.telework.day'].search([
                ('date', '=', context_date),
                ('mode', '=', 'onsite'),
                ('workstation_id', 'in', self.ids),
                ('state', 'in', ['confirmed', 'draft'])
            ])
            occupied_ids = set(
                occupied_declarations.mapped('workstation_id.id')
            )

        for record in self:
            name = f"[{record.office_name}] {record.name}"
            if record.department_id:
                name += f" ({record.department_id.name})"

            # Mark occupied workstations
            if record.id in occupied_ids:
                name = f"{name} - OCCUPIED"

            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100,
                     name_get_uid=None):
        """Search by name, office or department, prioritize available ones"""
        if args is None:
            args = []

        if name:
            # Clean the search term to handle composed names
            clean_name = name.strip()

            # Extract parts if it's in format [Office] Name (Department)
            office_part = ''
            workstation_part = clean_name

            if '[' in clean_name and ']' in clean_name:
                parts = clean_name.split(']', 1)
                office_part = parts[0].strip('[]').strip()
                if len(parts) > 1:
                    workstation_part = parts[1].strip()
                    # Remove department part if exists
                    if '(' in workstation_part:
                        workstation_part = workstation_part.split('(')[0]
                        workstation_part = workstation_part.strip()

            # Build search domain
            domain = ['|', '|', '|']
            domain.extend([
                ('name', operator, clean_name),
                ('office_id.name', operator, clean_name),
                ('department_id.name', operator, clean_name),
            ])

            # Add specific searches for extracted parts
            if office_part:
                domain.extend(['|', ('office_id.name', operator, office_part)])
            if workstation_part and workstation_part != clean_name:
                domain.extend(['|', ('name', operator, workstation_part)])

            args = domain + args

        # Get basic search results
        workstation_ids = super()._name_search(
            name=name, args=args, operator=operator, limit=limit,
            name_get_uid=name_get_uid)

        # If we have a context date, reorder to show available ones first
        context_date = self.env.context.get('date_context')
        if context_date and workstation_ids:
            # workstation_ids is a list of integers, not tuples
            workstations = self.browse(workstation_ids)

            # Get occupied workstation IDs for this date
            occupied_declarations = self.env['hr.telework.day'].search([
                ('date', '=', context_date),
                ('mode', '=', 'onsite'),
                ('workstation_id', 'in', workstations.ids),
                ('state', 'in', ['confirmed', 'draft'])
            ])
            occupied_ids = set(
                occupied_declarations.mapped('workstation_id.id')
            )

            # Separate available and occupied workstations
            available = workstations.filtered(
                lambda w: w.id not in occupied_ids
            )
            occupied = workstations.filtered(
                lambda w: w.id in occupied_ids
            )

            # Return ordered list: available first, then occupied
            ordered_workstations = available + occupied
            return ordered_workstations.ids

        return workstation_ids

    def action_view_declarations(self):
        """View declarations for this workstation"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Declarations for %s') % self.name,
            'res_model': 'hr.telework.day',
            'view_mode': 'tree,form',
            'domain': [('workstation_id', '=', self.id)],
            'context': {'default_workstation_id': self.id},
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Invalidate office cache when creating workstations"""
        records = super().create(vals_list)
        # Invalidate cache of related offices
        offices = records.mapped('office_id')
        if offices:
            offices.invalidate_recordset(['workstation_ids'])
        return records

    def write(self, vals):
        """Invalidate office cache when modifying workstations"""
        old_offices = self.mapped('office_id')
        result = super().write(vals)
        # Invalidate cache of old and new offices
        new_offices = self.mapped('office_id')
        all_offices = old_offices | new_offices
        if all_offices:
            all_offices.invalidate_recordset(['workstation_ids'])
        return result

    def unlink(self):
        """Invalidate office cache when deleting workstations"""
        offices = self.mapped('office_id')
        result = super().unlink()
        # Invalidate cache of related offices
        if offices:
            offices.invalidate_recordset(['workstation_ids'])
        return result
