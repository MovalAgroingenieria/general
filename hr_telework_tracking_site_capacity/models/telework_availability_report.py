# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models, tools


class HrTeleworkAvailabilityReport(models.Model):
    _name = 'hr.telework.availability.report'
    _description = 'Telework Availability Report'
    _auto = False
    _order = 'date desc, office_id'

    date = fields.Date(string='Date', readonly=True)
    date_label = fields.Char(string='Date Label', readonly=True)
    office_id = fields.Many2one('office.location', string='Office', readonly=True)
    occupied_count = fields.Integer(string='Occupied', readonly=True)
    capacity = fields.Integer(string='Capacity', readonly=True)
    availability_display = fields.Char(string='Occupancy', readonly=True)
    occupancy_percentage = fields.Float(string='Occupancy %', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW hr_telework_availability_report AS (
                SELECT
                    row_number() OVER (ORDER BY d.date, o.id) as id,
                    d.date as date,
                    to_char(d.date, 'DD/MM/YYYY') as date_label,
                    o.id as office_id,
                    count(t.id) as occupied_count,
                    o.capacity as capacity,
                    concat(count(t.id), '/', o.capacity) as availability_display,
                    CASE
                        WHEN o.capacity > 0 THEN (count(t.id)::float / o.capacity::float) * 100
                        ELSE 0
                    END as occupancy_percentage
                FROM
                    (SELECT DISTINCT date FROM hr_telework_day WHERE date IS NOT NULL) d
                    CROSS JOIN office_location o
                    LEFT JOIN hr_telework_day t ON (
                        t.date = d.date AND
                        t.office_id = o.id AND
                        t.mode = 'onsite' AND
                        t.state IN ('confirmed', 'draft', 'pending_review')
                    )
                WHERE o.active = true
                GROUP BY
                    d.date,
                    o.id,
                    o.capacity
            )
        """)
