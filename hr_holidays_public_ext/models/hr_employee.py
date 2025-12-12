# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, tools


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    def _register_hook(self):
        super()._register_hook()
        self.init()
