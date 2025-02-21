# -*- coding: utf-8 -*-
# Copyright 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import pytz
import datetime
from Crypto import Random
from Crypto.Cipher import AES
from odoo import models, fields, api, _


class EomDigitalregister(models.Model):
    _name = 'eom.digitalregister'
    _description = 'Digital Register'
    _order = 'fullname'

    SIZE_NAME = 20
    SIZE_FIRSTNAME = 50
    SIZE_LASTNAME = 50
    SIZE_AUTHORITY = 50

    # IMPORTANT: This cipher key must be replaced in the custom module (and
    # in the related PHP). Or preferably in a new custom module that is
    # outside the repository (in this way, it is outside the AGPL license and
    # does not have to be delivered).
    _cipher_key = 'a%C*F-JaNdRgUkXqj8Ymx59IYhv0vHe2'

    name = fields.Char(
        string='VAT',
        size=SIZE_NAME,
        required=True,
        index=True,)

    firstname = fields.Char(
        string='First Name',
        size=SIZE_FIRSTNAME,
        index=True,)

    lastname = fields.Char(
        string='Last Name',
        size=SIZE_LASTNAME,
        index=True,)

    authority = fields.Char(
        string='Authority',
        size=SIZE_AUTHORITY,
        index=True,)

    partner_id = fields.Many2one(
        string='Partner',
        comodel_name='res.partner',
        index=True,
        ondelete='restrict',)

    digitalregisteraccess_ids = fields.One2many(
        string='Accesses of the digital certificate',
        comodel_name='eom.digitalregister.access',
        inverse_name='digitalregister_id')

    editable_notes = fields.Boolean(
        string='Editable Notes (y/n)',
        compute='_compute_editable_notes',)

    notes = fields.Html(
        string='Notes',)

    fullname = fields.Char(
        string='Full Name',
        store=True,
        compute='_compute_fullname',
        index=True,)

    fullname_html = fields.Html(
        string="Full Name (html)",
        compute='_compute_fullname_html',)

    fullname_firstname = fields.Char(
        string="Full Name (firstname and lastname)",
        compute='_compute_fullname_firstname',)

    last_event_time = fields.Datetime(
        string='Last Access',
        compute='_compute_last_event_time',)

    number_of_accesses = fields.Integer(
        string='Number of accesses',
        compute='_compute_number_of_accesses',)

    number_of_requests = fields.Integer(
        string='Number of requests',
        compute='_compute_number_of_requests',)

    email = fields.Char(
        string='Email',
        related='partner_id.email',)

    phone = fields.Char(
        string='Phone',
        related='partner_id.phone',)

    mobile = fields.Char(
        string='Mobile',
        related='partner_id.mobile',)

    icon_with_contact = fields.Char(
        string='With contact (icon)',
        compute='_compute_icon_with_contact',)

    image = fields.Binary(
        string='Image',
        compute='_compute_image')

    image_small = fields.Binary(
        string='Image (small)',
        compute='_compute_image_small')

    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('unique_name', 'UNIQUE (name)',
         'Existing digital certificate.'),
        ]

    def _compute_editable_notes(self):
        editable_notes = self.env['ir.default'].get(
            'res.eom.config.settings', 'editable_notes')
        for record in self:
            record.editable_notes = editable_notes

    @api.depends('firstname', 'lastname')
    def _compute_fullname(self):
        for record in self:
            fullname = ''
            if record.lastname:
                fullname = record.lastname
                if record.firstname:
                    fullname = fullname + ' ' + record.firstname
            elif record.firstname:
                fullname = record.firstname
            record.fullname = fullname

    def _compute_fullname_html(self):
        for record in self:
            fullname_html = ''
            if record.lastname:
                fullname_html = record.lastname
                if record.firstname:
                    fullname_html = fullname_html + '<br/>' + \
                        record.firstname
            elif record.firstname:
                fullname_html = record.firstname
            record.fullname_html = fullname_html

    def _compute_fullname_firstname(self):
        for record in self:
            fullname_firstname = ''
            if record.firstname:
                fullname_firstname = record.firstname
                if record.lastname:
                    fullname_firstname = fullname_firstname + ' ' + \
                        record.lastname
                elif record.lastname:
                    fullname_firstname = record.lastname
            record.fullname_firstname = fullname_firstname

    def _compute_last_event_time(self):
        for record in self:
            last_event_time = None
            self.env.cr.execute("""
                SELECT MAX(event_time)
                FROM eom_digitalregister_access
                WHERE digitalregister_id = """ + str(record.id) + """
                """)
            query_results = self.env.cr.dictfetchall()
            if query_results:
                last_event_time = query_results[0].get('max')
            record.last_event_time = last_event_time

    def _compute_number_of_accesses(self):
        for record in self:
            number_of_accesses = 0
            self.env.cr.execute("""
                SELECT COUNT(*)
                FROM eom_digitalregister_access
                WHERE digitalregister_id = """ + str(record.id) + """
                """)
            query_results = self.env.cr.dictfetchall()
            if query_results:
                number_of_accesses = query_results[0].get('count')
            record.number_of_accesses = number_of_accesses

    def _compute_number_of_requests(self):
        for record in self:
            number_of_requests = 0
            self.env.cr.execute("""
                SELECT COUNT(*)
                FROM eom_digitalregister_access
                WHERE digitalregister_id = """ + str(record.id) + """
                AND with_userdata""")
            query_results = self.env.cr.dictfetchall()
            if query_results:
                number_of_requests = query_results[0].get('count')
            record.number_of_requests = number_of_requests

    def _compute_icon_with_contact(self):
        for record in self:
            icon_with_contact = ''
            if record.partner_id:
                icon_with_contact = '👤'
            record.icon_with_contact = icon_with_contact

    def _compute_image(self):
        for record in self:
            image = None
            if record.partner_id:
                image = record.partner_id.image_medium
            record.image = image

    def _compute_image_small(self):
        for record in self:
            image_small = None
            if record.partner_id:
                image_small = record.partner_id.image_small
            record.image_small = image_small

    def name_get(self):
        result = []
        reduced_register_id = \
            self.env.context.get('reduced_register_id', False)
        for record in self:
            name = record.name
            if not reduced_register_id:
                name = name + ' (' + record.fullname_firstname + ')'
            result.append((record.id, name))
        return result

    @api.model
    def encrypt_data(self, data_to_encrypt):
        resp = ''
        cipher_key = self._cipher_key
        if data_to_encrypt and cipher_key:
            # Adaptation of cipher_key
            limit = 16
            len_cipher_key = len(cipher_key)
            if len_cipher_key > 16 and len_cipher_key <= 24:
                limit = 24
            elif len_cipher_key > 24:
                limit = 32
            if len_cipher_key < limit:
                cipher_key = cipher_key + ' ' * (limit - len_cipher_key)
            if len_cipher_key > limit:
                cipher_key = cipher_key[:limit]
            # Adaptation for 16-multiple
            block_size = AES.block_size
            data_to_encrypt = data_to_encrypt.encode('utf-8')
            len_of_data_to_encrypt = len(data_to_encrypt)
            rest = len_of_data_to_encrypt % block_size
            if rest > 0:
                data_to_encrypt = data_to_encrypt + b' ' * (block_size - rest)
            # Encrypt
            iv = Random.new().read(AES.block_size)
            cipher = AES.new(cipher_key.encode('utf-8'), AES.MODE_CBC, iv)
            encrypted_data = cipher.encrypt(data_to_encrypt)
            # Coding to base64
            resp = base64.b64encode(iv + encrypted_data)
        return resp

    @api.model
    def decrypt_data(self, encrypted_data):
        resp = ''
        cipher_key = self._cipher_key
        if encrypted_data and cipher_key:
            block_size = AES.block_size
            # Decoding from base64
            try:
                encrypted_content = base64.b64decode(encrypted_data)
            except Exception:
                encrypted_content = ''
            if len(encrypted_content) > block_size:
                # Extract iv and encrypted data without iv
                iv = encrypted_content[:block_size]
                encrypted_data = encrypted_content[block_size:]
                # Adaptation of cipher_key
                limit = 16
                len_cipher_key = len(cipher_key)
                if len_cipher_key > 16 and len_cipher_key <= 24:
                    limit = 24
                elif len_cipher_key > 24:
                    limit = 32
                if len_cipher_key < limit:
                    cipher_key = cipher_key + ' ' * (limit - len_cipher_key)
                if len_cipher_key > limit:
                    cipher_key = cipher_key[:limit]
                # Decrypt
                cipher = AES.new(cipher_key.encode('utf-8'), AES.MODE_CBC, iv)
                raw_decrypted_data = cipher.decrypt(encrypted_data)
                resp = raw_decrypted_data.rstrip().decode('utf-8')
        return resp

    @api.model
    def get_items_of_decrypted_identif(self, decrypted_identif):
        country = ''
        dni = ''
        firstname = ''
        lastname = ''
        authority = ''
        item_list = decrypted_identif.split(':')
        if item_list and len(item_list) >= 5:
            country = item_list[0]
            dni = item_list[1]
            firstname = item_list[3]
            lastname = item_list[2]
            authority = item_list[4]
        return country, dni, firstname, lastname, authority

    @api.model
    def create_access(self, dni, firstname, lastname, authority):
        if dni and firstname and lastname and authority:
            # First: if the record does not exist in the "eom.digitalregister"
            # model, it is mandatory to create it.
            digitalregister = self.search([('name', '=', dni)])
            if not digitalregister:
                vals = {
                    'name': dni,
                    'firstname': firstname,
                    'lastname': lastname,
                    'authority': authority,
                    }
                partner_id = None
                model_res_partner = self.env['res.partner']
                possible_partners = model_res_partner.search(
                    [('vat', '=', dni)])
                if possible_partners and len(possible_partners) == 1:
                    partner_id = possible_partners[0].id
                if partner_id:
                    vals['partner_id'] = partner_id
                digitalregister = self.create(vals)
            else:
                digitalregister = digitalregister[0]
            # Second: add the access to digital register.
            model_digitalregister_access = \
                self.env['eom.digitalregister.access']
            new_access = model_digitalregister_access.create({
                'digitalregister_id': digitalregister.id, })
            # digitalregister.write({
            #     'digitalregisteraccess_ids': [(0, 0, {})]
            #     })
            return new_access
        else:
            return False

    def action_accesses(self):
        self.ensure_one()
        current_digitalregister = self
        id_kanban_view = self.env.ref(
            'eom_authdnie.eom_digitalregister_access_view_kanban').id
        id_tree_view = self.env.ref(
            'eom_authdnie.eom_digitalregister_access_view_tree').id
        id_form_view = self.env.ref(
            'eom_authdnie.eom_digitalregister_access_view_form').id
        search_view = self.env.ref(
            'eom_authdnie.eom_digitalregister_access_view_search')
        act_window = {
            'type': 'ir.actions.act_window',
            'name': _('Accesses'),
            'res_model': 'eom.digitalregister.access',
            'view_type': 'form',
            'view_mode': 'kanban,form,tree',
            'views': [(id_kanban_view, 'kanban'), (id_tree_view, 'tree'),
                      (id_form_view, 'form')],
            'search_view_id': [search_view.id],
            'target': 'current',
            'domain': [('digitalregister_id', '=',
                        current_digitalregister.id)],
            'context': {'hide_image': True,
                        'search_default_grouped_event_time': True,
                        'reduced_register_id': True,
                        'reduced_access_id': True, },
            }
        return act_window

    def action_requests(self):
        self.ensure_one()
        current_digitalregister = self
        id_kanban_view = self.env.ref(
            'eom_authdnie.eom_digitalregister_access_view_kanban').id
        id_tree_view = self.env.ref(
            'eom_authdnie.eom_digitalregister_access_view_tree').id
        id_form_view = self.env.ref(
            'eom_authdnie.eom_digitalregister_access_view_form').id
        search_view = self.env.ref(
            'eom_authdnie.eom_digitalregister_access_view_search')
        act_window = {
            'type': 'ir.actions.act_window',
            'name': _('Requests'),
            'res_model': 'eom.digitalregister.access',
            'view_type': 'form',
            'view_mode': 'kanban,form,tree',
            'views': [(id_kanban_view, 'kanban'), (id_tree_view, 'tree'),
                      (id_form_view, 'form')],
            'search_view_id': [search_view.id],
            'target': 'current',
            'domain': [('digitalregister_id', '=', current_digitalregister.id),
                       ('with_userdata', '=', True)],
            'context': {'hide_image': True,
                        'search_default_grouped_event_time': True,
                        'reduced_register_id': True,
                        'reduced_access_id': True, },
            }
        return act_window


class EomDigitalregisterAccess(models.Model):
    _name = 'eom.digitalregister.access'
    _description = 'Access of a digital register'
    _order = 'event_time desc'

    SIZE_NAME = 50
    SIZE_SUMMARY = 75
    SIZE_DETAIL = 255

    event_time = fields.Datetime(
        string='Time',
        default=lambda self: fields.datetime.now(),
        required=True,
        index=True,
        readonly=True,)

    digitalregister_id = fields.Many2one(
        string='Digital Certificate',
        comodel_name='eom.digitalregister',
        required=True,
        index=True,
        readonly=True,
        ondelete='cascade',)

    name = fields.Char(
        size=SIZE_NAME,
        store=True,
        index=True,
        compute='_compute_name',)

    partner_id = fields.Many2one(
        string='Partner',
        comodel_name='res.partner',
        store=True,
        index=True,
        compute='_compute_partner_id',
        ondelete='restrict',)

    summary = fields.Char(
        string='Summary',
        size=SIZE_SUMMARY,
        index=True,)

    detail = fields.Char(
        string='Detail',
        size=SIZE_DETAIL,)

    detail_text = fields.Text(
        string='Detail (text)',
        compute='_compute_detail_text',)

    editable_notes = fields.Boolean(
        string='Editable Notes (y/n)',
        compute='_compute_editable_notes',)

    with_userdata = fields.Boolean(
        string='With user data (y/n)',
        store=True,
        compute='_compute_with_userdata',)

    notes = fields.Html(
        string='Notes',)

    icon_with_userdata = fields.Char(
        string='With user data (icon)',
        compute='_compute_icon_with_userdata',)

    firstname = fields.Char(
        string='First Name',
        store=True,
        compute='_compute_firstname',
        index=True,)

    lastname = fields.Char(
        string='Last Name',
        store=True,
        compute='_compute_lastname',
        index=True,)

    authority = fields.Char(
        string='Authority',
        related='digitalregister_id.authority',)

    icon_with_contact = fields.Char(
        string='With contact (icon)',
        related='digitalregister_id.icon_with_contact',)

    image = fields.Binary(
        string='Image',
        compute='_compute_image')

    image_small = fields.Binary(
        string='Image (small)',
        compute='_compute_image_small')

    fullname = fields.Char(
        string='Full Name',
        store=True,
        compute='_compute_fullname',
        index=True,)

    fullname_html = fields.Html(
        string="Full Name (html)",
        compute='_compute_fullname_html',)

    fullname_firstname = fields.Char(
        string="Full Name (firstname and lastname)",
        compute='_compute_fullname_firstname',)

    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('unique_name', 'UNIQUE (name)',
         'Existing access.'),
        ]

    @api.depends('event_time', 'digitalregister_id')
    def _compute_name(self):
        for record in self:
            name = ''
            if record.event_time and record.digitalregister_id:
                name = str(record.event_time) + '-' + \
                    record.digitalregister_id.name
            record.name = name

    @api.depends('digitalregister_id', 'digitalregister_id.partner_id')
    def _compute_partner_id(self):
        for record in self:
            partner_id = None
            if (record.digitalregister_id and
               record.digitalregister_id.partner_id):
                partner_id = record.digitalregister_id.partner_id
            record.partner_id = partner_id

    def _compute_detail_text(self):
        for record in self:
            record.detail_text = record.detail

    def _compute_editable_notes(self):
        editable_notes = self.env['ir.default'].get(
            'res.eom.config.settings', 'editable_notes')
        for record in self:
            record.editable_notes = editable_notes

    @api.depends('summary')
    def _compute_with_userdata(self):
        for record in self:
            with_userdata = False
            if record.summary:
                with_userdata = True
            record.with_userdata = with_userdata

    def _compute_icon_with_userdata(self):
        for record in self:
            icon_with_userdata = ''
            if record.with_userdata:
                icon_with_userdata = '📝'
            record.icon_with_userdata = icon_with_userdata

    @api.depends('digitalregister_id', 'digitalregister_id.firstname')
    def _compute_firstname(self):
        for record in self:
            firstname = ''
            if (record.digitalregister_id and
               record.digitalregister_id.firstname):
                firstname = record.digitalregister_id.firstname
            record.firstname = firstname

    @api.depends('digitalregister_id', 'digitalregister_id.lastname')
    def _compute_lastname(self):
        for record in self:
            lastname = ''
            if (record.digitalregister_id and
               record.digitalregister_id.lastname):
                lastname = record.digitalregister_id.lastname
            record.lastname = lastname

    @api.depends('digitalregister_id',
                 'digitalregister_id.firstname', 'digitalregister_id.lastname')
    def _compute_fullname(self):
        for record in self:
            fullname = ''
            if record.digitalregister_id:
                if record.digitalregister_id.lastname:
                    fullname = record.digitalregister_id.lastname
                    if record.digitalregister_id.firstname:
                        fullname = fullname + ' ' + \
                            record.digitalregister_id.firstname
                elif record.digitalregister_id.firstname:
                    fullname = record.digitalregister_id.firstname
            record.fullname = fullname

    def _compute_fullname_html(self):
        for record in self:
            fullname_html = ''
            if record.lastname:
                fullname_html = record.lastname
                if record.firstname:
                    fullname_html = fullname_html + '<br/>' + \
                        record.firstname
            elif record.firstname:
                fullname_html = record.firstname
            record.fullname_html = fullname_html

    def _compute_fullname_firstname(self):
        for record in self:
            fullname_firstname = ''
            if record.firstname:
                fullname_firstname = record.firstname
                if record.lastname:
                    fullname_firstname = fullname_firstname + ' ' + \
                        record.lastname
                elif record.lastname:
                    fullname_firstname = record.lastname
            record.fullname_firstname = fullname_firstname

    def _compute_image(self):
        for record in self:
            image = None
            if record.partner_id:
                image = record.partner_id.image_medium
            record.image = image

    def _compute_image_small(self):
        for record in self:
            image_small = None
            if record.partner_id:
                image_small = record.partner_id.image_small
            record.image_small = image_small

    def name_get(self):
        result = []
        reduced_access_id = \
            self.env.context.get('reduced_access_id', False)
        for record in self:
            event_time = \
                fields.Datetime.from_string(record.event_time)
            if self.env.user.tz:
                local_timezone = pytz.timezone(self.env.user.tz)
                offset = local_timezone.utcoffset(event_time)
                event_time = event_time + offset
            event_time_str = str(event_time)
            date_str = event_time_str[:10]
            hour_str = event_time_str[-8:]
            name = datetime.datetime.strptime(
                date_str, '%Y-%m-%d').strftime('%x') + ' ' + hour_str
            if not reduced_access_id:
                name = record.digitalregister_id.name + ' (' + \
                    record.digitalregister_id.fullname_firstname + ')' + \
                    ', ' + name
            result.append((record.id, name))
        return result

    @api.model
    def update_access(self, access_name, summary, detail):
        resp = False
        if summary:
            access = self.search([('name', '=', access_name)])
            if access:
                vals = {'summary': summary}
                if detail:
                    vals['detail'] = detail
                access.write(vals)
                resp = True
        return resp
