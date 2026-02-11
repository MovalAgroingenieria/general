# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import random
import string
import uuid
from datetime import timedelta

from odoo import models, fields, api

MAX_ATTEMPTS = 5
CODE_LENGTH = 6
CODE_EXPIRY_MINUTES = 10


class LoginVerification(models.Model):
    _name = 'login.verification'
    _description = 'Login Verification Code'
    _order = 'create_date desc'

    token = fields.Char(
        string='Token', required=True, index=True)
    user_login = fields.Char(
        string='User Login', required=True)
    user_password = fields.Char(
        string='Temporary Auth Token', required=True)
    database = fields.Char(
        string='Database')
    contact_mail = fields.Char(
        string='Contact Email', required=True)
    phone = fields.Char(
        string='Phone')
    company = fields.Char(
        string='Company')
    country = fields.Char(
        string='Country')
    verification_code = fields.Char(
        string='Verification Code', required=True)
    code_expiry = fields.Datetime(
        string='Code Expiry', required=True, index=True)
    redirect = fields.Char(
        string='Redirect URL')
    attempts = fields.Integer(
        string='Attempts', default=0)
    last_sent = fields.Datetime(
        string='Last Sent')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('expired', 'Expired'),
        ('failed', 'Failed'),
    ], string='State', default='pending', index=True)

    @api.model
    def generate_verification(self, login, password, db, contact_mail,
                              phone='', company='', country='',
                              redirect=''):
        """Generate a new verification record with a random code."""
        code = ''.join(
            [random.choice(string.digits) for _ in range(CODE_LENGTH)])
        token = uuid.uuid4().hex
        now_dt = fields.Datetime.from_string(fields.Datetime.now())
        expiry = fields.Datetime.to_string(
            now_dt + timedelta(minutes=CODE_EXPIRY_MINUTES))

        record = self.create({
            'token': token,
            'user_login': login,
            'user_password': password,
            'database': db,
            'contact_mail': contact_mail,
            'phone': phone,
            'company': company,
            'country': country,
            'verification_code': code,
            'code_expiry': expiry,
            'redirect': redirect,
            'last_sent': fields.Datetime.now(),
        })
        return record

    @api.model
    def cleanup_expired(self):
        """Remove expired and completed verification records."""
        expired = self.search([
            '|',
            ('code_expiry', '<', fields.Datetime.now()),
            ('state', 'in', ['verified', 'failed']),
        ])
        expired.unlink()

    @api.multi
    def is_expired(self):
        """Check if the verification code has expired."""
        self.ensure_one()
        return (self.code_expiry < fields.Datetime.now()
                or self.state != 'pending')

    @api.multi
    def verify_code(self, code):
        """Verify the submitted code.

        Returns True if correct, False otherwise.
        Updates state to 'failed' after MAX_ATTEMPTS wrong attempts,
        and to 'expired' if the code has expired.
        """
        self.ensure_one()

        if self.is_expired():
            self.state = 'expired'
            return False

        if self.attempts >= MAX_ATTEMPTS:
            self.state = 'failed'
            return False

        self.attempts += 1

        if self.verification_code == code:
            self.state = 'verified'
            return True

        if self.attempts >= MAX_ATTEMPTS:
            self.state = 'failed'

        return False
