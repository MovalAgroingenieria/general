# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from odoo import api

_logger = logging.getLogger(__name__)


def post_load_hook():
    """
    Monkey patch HrEmployeePublic._get_fields to ensure it always fetches
    all columns from the database, preventing view breakage during updates.
    """
    from odoo.addons.hr.models.hr_employee_public import HrEmployeePublic

    _logger.info("HrHolidaysPublicExt: Patching HrEmployeePublic._get_fields")

    @api.model
    def _get_fields_patched(self):
        # Use information_schema to get ALL columns, ensuring the view is never broken
        # even if the registry is incomplete during an update.
        self.env.cr.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'hr_employee'
            ORDER BY ordinal_position
        """)
        columns = [row[0] for row in self.env.cr.fetchall()]
        return ','.join('emp."%s"' % col for col in columns)

    HrEmployeePublic._get_fields = _get_fields_patched
