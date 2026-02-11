# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class ClientData(models.Model):
    _name = 'client.data'
    _description = 'Client Connect Information'

    database = fields.Char(name='database', string='Database')
    mail = fields.Char(name='email', string='Email')
    phone = fields.Char(name='phone', string='Phone')
    company = fields.Char(name='company', string='Company')
    country = fields.Char(name='country', string='Country')
    ip_address = fields.Char(string='IP Address')

    @api.model
    def create(self, vals):
        record = super(ClientData, self).create(vals)
        self.send_new_user_mail(record)
        return record

    @api.model
    def send_new_user_mail(self, user):
        template_id = self.env.ref('client_connect.'
                                   'new_user_mail_template').id
        template = self.env['mail.template'].browse(template_id)
        if 'moval' not in user.mail:
            template.body_html = u'''
                <table style="border-collapse: collapse;">
                    <tr>
                        <th style="border: 1px solid black; padding: 5px;
                        text-align: center;">Database</th>
                        <th style="border: 1px solid black; padding: 5px;
                        text-align: center;">Email</th>
                        <th style="border: 1px solid black; padding: 5px;
                        text-align: center;">Phone</th>
                        <th style="border: 1px solid black; padding: 5px;
                        text-align: center;">Company</th>
                        <th style="border: 1px solid black; padding: 5px;
                        text-align: center;">Country</th>
                    </tr>
                    <tr>
                        <td style="border: 1px solid black; padding: 5px;
                        text-align: center;">{}</td>
                        <td style="border: 1px solid black; padding: 5px;
                        text-align: center;">{}</td>
                        <td style="border: 1px solid black; padding: 5px;
                        text-align: center;">{}</td>
                        <td style="border: 1px solid black; padding: 5px;
                        text-align: center;">{}</td>
                        <td style="border: 1px solid black; padding: 5px;
                        text-align: center;">{}</td>
                    </tr>
                </table>
            '''.format(user.database, user.mail, user.phone or "",
                       user.company or "", user.country or "")
            template.send_mail(user.id, force_send=True)
