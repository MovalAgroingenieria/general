# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, tools, _


class SmsSms(models.Model):
    _inherit = 'sms.sms'

    wausms_response = fields.Text(
        string="WausSMS Response")
