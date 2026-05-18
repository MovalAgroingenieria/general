# -*- coding: utf-8 -*-
# 2021 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class NRSConfiguration(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = 'nrs.configuration'

    service_url = fields.Char(
        string="Service URL",
        required=True)

    service_user = fields.Char(
        string="User",
        required=True)

    service_passwd = fields.Char(
        string="Password",
        required=True)

    default_sender = fields.Char(
        string="Sender",
        required=True,
        size=15,
        help="The sender that will appear in all messages. Limit to 15 "
             "numbers (only numbers) or 11 alphanumeric characters.")

    test_phone_number = fields.Char(
        string="Test phone number",
        size=15,
        help="For test configuration\nHave to be saved before to be "
             "used.\nOnly Spanish mobile numbers")

    default_partner_template_id = fields.Many2one(
        comodel_name='nrs.template',
        string='Partner',
        ondelete="set null")

    default_invoice_template_id = fields.Many2one(
        comodel_name='nrs.template',
        string='Invoice',
        ondelete="set null")

    show_icon_next_mobile_certified = fields.Boolean(
        string="Show icon next to mobile",
        default=True,
        help="If it is checked, it shows an icon next to the mobile to send "
             "SMS.")

    show_icon_on_partner_view_kanban_certified = fields.Boolean(
        string="Show icon in kanban card",
        default=True,
        help="If checked, it shows an icon in the upper right corner of the "
             "kanban card to send SMS.")

    allow_certify_sms = fields.Boolean(
        string="Allow certify SMS",
        default=True,
        help="If checked, it is allowed to send certified SMS. They have an "
             "additional cost.")

    allow_flash_sms = fields.Boolean(
        string="Allow flash SMS",
        default=False,
        help="If checked, it is allowed to send flash SMS. These SMS appear "
             "directly on the device screen. Be careful, on some devices these"
             " SMS cannot be saved.")

    @api.multi
    def set_default_values(self):
        values = self.env['ir.values'].sudo()
        values.set_default('nrs.configuration',
                           'service_url',
                           self.service_url)
        values.set_default('nrs.configuration',
                           'service_user',
                           self.service_user)
        values.set_default('nrs.configuration',
                           'service_passwd',
                           self.service_passwd)
        values.set_default('nrs.configuration',
                           'default_sender',
                           self.default_sender)
        values.set_default('nrs.configuration',
                           'test_phone_number',
                           self.test_phone_number)
        values.set_default('nrs.configuration',
                           'default_partner_template_id',
                           self.default_partner_template_id.id)
        values.set_default('nrs.configuration',
                           'default_invoice_template_id',
                           self.default_invoice_template_id.id)
        values.set_default('nrs.configuration',
                           'show_icon_next_mobile_certified',
                           self.show_icon_next_mobile_certified)
        values.set_default('nrs.configuration',
                           'show_icon_on_partner_view_kanban_certified',
                           self.show_icon_on_partner_view_kanban_certified)
        values.set_default('nrs.configuration', 'allow_certify_sms',
                           self.allow_certify_sms)
        values.set_default('nrs.configuration', 'allow_flash_sms',
                           self.allow_flash_sms)

    @api.constrains('default_sender')
    def _check_default_sender_size(self):
        if not self.default_sender.isdigit() and len(self.default_sender) > 11:
            raise ValidationError(_("Sender size is limited to 15 numbers "
                                    "(ex. 34XXXXXXXXX) or 11 alphanumeric "
                                    "characters (ex. company xxx)"))
