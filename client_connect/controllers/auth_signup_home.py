# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import random
import string
from datetime import timedelta

from odoo import _, http, fields
from odoo.http import request
from odoo.addons.web.controllers.main import Home

# Rate limit: minimum seconds between verification code requests
# per contact email
RATE_LIMIT_SECONDS = 60


class CustomSessionController(Home):

    @http.route('/web/login', type='http', auth='none', website=True)
    def web_login(self, redirect=None, **kw):
        response = super(CustomSessionController, self).web_login(
            redirect=redirect, **kw)

        countries = request.env['res.country'].sudo().search([])
        response.qcontext['countries'] = countries

        lang_list = request.env['res.lang'].sudo().search([])
        response.qcontext['lang_list'] = lang_list

        # Check if internal mode is active (skip contact fields
        # and email verification)
        internal = kw.get('internal', '') == '1'
        response.qcontext['internal'] = internal

        # If the login was successful
        if request.httprequest.method == 'POST' and request.session.uid:

            if internal:
                # Internal mode: skip verification, allow direct
                # login without contact fields
                return response

            # External mode: require email verification
            contact_mail = kw.get('mail', '')

            if not contact_mail:
                # No contact mail provided: logout and show error
                request.session.logout(keep_db=True)
                response.qcontext['error'] = _(
                    'Contact Mail is required for verification.')
                return response

            login = kw.get('login', '')
            password = kw.get('password', '')
            db = request.db

            # Rate limit: check if a recent verification was sent
            # to this email
            Verification = request.env['login.verification'].sudo()
            recent = Verification.search([
                ('contact_mail', '=', contact_mail),
                ('state', '=', 'pending'),
            ], order='create_date desc', limit=1)
            if recent and recent.last_sent:
                last_sent = fields.Datetime.from_string(
                    recent.last_sent)
                now = fields.Datetime.from_string(
                    fields.Datetime.now())
                if (now - last_sent).total_seconds() \
                        < RATE_LIMIT_SECONDS:
                    # Rate limited: redirect to existing
                    # verification page
                    request.session.logout(keep_db=True)
                    return http.redirect_with_hash(
                        '/web/login/verify?token=%s'
                        % recent.token)

            # Encode password for temporary storage (base64)
            if isinstance(password, unicode):
                encoded_pw = base64.b64encode(password.encode('utf-8'))
            else:
                encoded_pw = base64.b64encode(password)

            # Create verification record (while still authenticated)
            verification = Verification.generate_verification(
                login=login,
                password=encoded_pw,
                db=db,
                contact_mail=contact_mail,
                phone=kw.get('phone', ''),
                company=kw.get('company', ''),
                country=kw.get('country', ''),
                redirect=redirect or '',
            )

            # Send verification code email
            user = request.env['res.users'].sudo().browse(
                request.session.uid)
            lang = user.lang or 'es_ES'
            self._send_verification_email(
                contact_mail, verification.verification_code,
                lang=lang)

            # Cleanup old verification records
            Verification.cleanup_expired()

            # Logout the user (verification required first)
            request.session.logout(keep_db=True)

            # Redirect to verification page
            return http.redirect_with_hash(
                '/web/login/verify?token=%s' % verification.token)

        return response

    def _send_verification_email(self, email, code, lang=None):
        """Send the verification code to the user's contact email."""
        lang = lang or 'es_ES'

        # Direct translation lookup — _() frame introspection
        # is unreliable in public/none-auth controllers.
        def _t(source):
            translated = request.env[
                'ir.translation'].sudo()._get_source(
                None, ('code', 'model'), lang, source)
            return translated or source

        # Find a real mail server (skip fake/dummy servers)
        mail_server = request.env['ir.mail_server'].sudo().search(
            [('smtp_host', '!=', 'fake')],
            order='sequence asc', limit=1)

        mail_values = {
            'email_from': 'info@moval.es',
            'email_to': email,
            'subject': _t(
                'Moval Demo - Your Login Verification Code'),
            'body_html': u'''
                <div style="font-family: Arial, sans-serif;
                    max-width: 500px; margin: 0 auto;">
                    <h2 style="color: #875A7B;">{title}</h2>
                    <p>{message}</p>
                    <div style="background-color: #f5f5f5;
                        padding: 20px; text-align: center;
                        margin: 20px 0; border-radius: 5px;">
                        <span style="font-size: 32px;
                            font-weight: bold; letter-spacing: 8px;
                            color: #333;">{code}</span>
                    </div>
                    <p style="color: #666;">{expiry}</p>
                    <p style="color: #999; font-size: 12px;">
                        {ignore}</p>
                </div>
            '''.format(
                title=_t('Verification Code'),
                message=_t('Your verification code to complete'
                           ' the login is:'),
                code=code,
                expiry=_t('This code will expire in'
                          ' <strong>10 minutes</strong>.'),
                ignore=_t('If you did not request this code,'
                          ' please ignore this email.'),
            ),
        }
        if mail_server:
            mail_values['mail_server_id'] = mail_server.id
        request.env['mail.mail'].sudo().create(mail_values).send()

    @http.route('/web/login/verify', type='http', auth='public',
                website=True)
    def web_login_verify(self, **kw):
        """Handle the verification code submission (step 2)."""
        token = kw.get('token', '')
        values = {
            'token': token,
            'hide_form': False,
            'error': None,
            'contact_mail': '',
        }

        if not token:
            return http.redirect_with_hash('/web/login')

        # Find the pending verification record
        Verification = request.env['login.verification'].sudo()
        verification = Verification.search([
            ('token', '=', token),
            ('state', '=', 'pending'),
        ], limit=1)

        if not verification:
            return http.redirect_with_hash('/web/login')

        values['contact_mail'] = verification.contact_mail

        # Compute seconds remaining before resend is allowed
        seconds_remaining = 0
        if verification.last_sent:
            last_sent_dt = fields.Datetime.from_string(
                verification.last_sent)
            now_dt = fields.Datetime.from_string(
                fields.Datetime.now())
            elapsed = (now_dt - last_sent_dt).total_seconds()
            if elapsed < RATE_LIMIT_SECONDS:
                seconds_remaining = int(
                    RATE_LIMIT_SECONDS - elapsed)
        values['seconds_remaining'] = seconds_remaining

        # Translate resend label for JS countdown
        user = request.env['res.users'].sudo().search(
            [('login', '=', verification.user_login)], limit=1)
        ulang = user.lang if user else 'es_ES'
        resend_trans = request.env[
            'ir.translation'].sudo()._get_source(
            None, ('code', 'model'), ulang, 'Resend code')
        values['resend_label'] = resend_trans or 'Resend code'

        if request.httprequest.method == 'POST':
            submitted_code = kw.get('verification_code', '')

            if verification.verify_code(submitted_code):
                # Code correct — complete the login
                db = verification.database or request.db
                login = verification.user_login
                stored_pw = verification.user_password
                # Decode the base64-encoded password
                password = base64.b64decode(
                    str(stored_pw))
                redirect_url = verification.redirect

                # Save verified client data
                ip_address = request.httprequest.environ.get(
                    'HTTP_X_FORWARDED_FOR',
                    request.httprequest.environ.get(
                        'REMOTE_ADDR', ''))
                if ip_address and ',' in ip_address:
                    ip_address = ip_address.split(',')[0].strip()
                request.env['client.data'].sudo().create({
                    'database': db,
                    'mail': verification.contact_mail,
                    'phone': verification.phone,
                    'company': verification.company,
                    'country': verification.country,
                    'ip_address': ip_address,
                })

                # Remove the verification record (sensitive data)
                verification.unlink()

                # Authenticate the user
                uid = request.session.authenticate(db, login, password)
                if uid:
                    return http.redirect_with_hash(
                        redirect_url or '/web')
                else:
                    return http.redirect_with_hash('/web/login')

            else:
                # Code incorrect
                if verification.state == 'failed':
                    verification.unlink()
                    values['error'] = _(
                        'Too many failed attempts. '
                        'Please start the login process again.')
                    values['hide_form'] = True
                elif verification.state == 'expired':
                    verification.unlink()
                    values['error'] = _(
                        'The verification code has expired. '
                        'Please start the login process again.')
                    values['hide_form'] = True
                else:
                    remaining = 5 - verification.attempts
                    values['error'] = (
                        _('Invalid verification code. '
                          'You have %d attempt(s) remaining.')
                        % remaining)

        response = request.render(
            'client_connect.login_verify', values)
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @http.route('/web/login/verify/resend', type='http', auth='public',
                website=True)
    def web_login_verify_resend(self, **kw):
        """Resend the verification code email."""
        token = kw.get('token', '')
        if not token:
            return http.redirect_with_hash('/web/login')

        Verification = request.env['login.verification'].sudo()
        verification = Verification.search([
            ('token', '=', token),
            ('state', '=', 'pending'),
        ], limit=1)

        if not verification:
            return http.redirect_with_hash('/web/login')

        # Rate limit: minimum 60 seconds between sends
        if verification.last_sent:
            last_sent = fields.Datetime.from_string(
                verification.last_sent)
            now = fields.Datetime.from_string(
                fields.Datetime.now())
            if (now - last_sent).total_seconds() < 60:
                return http.redirect_with_hash(
                    '/web/login/verify?token=%s' % token)

        # Generate new code and reset attempts
        new_code = ''.join(
            [random.choice(string.digits) for _ in range(6)])
        now_dt = fields.Datetime.from_string(fields.Datetime.now())
        verification.write({
            'verification_code': new_code,
            'code_expiry': fields.Datetime.to_string(
                now_dt + timedelta(minutes=10)),
            'attempts': 0,
            'last_sent': fields.Datetime.now(),
        })

        # Send the new code (resolve user lang for translation)
        user = request.env['res.users'].sudo().search(
            [('login', '=', verification.user_login)], limit=1)
        lang = user.lang if user else 'es_ES'
        self._send_verification_email(
            verification.contact_mail, new_code, lang=lang)

        return http.redirect_with_hash(
            '/web/login/verify?token=%s' % token)
