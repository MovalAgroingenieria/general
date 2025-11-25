# 2022 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    firstname = fields.Char("First name")
    lastname = fields.Char("Last name")
    lastname2 = fields.Char("Second last name")
