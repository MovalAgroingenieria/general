# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
import pytz

from babel.dates import format_datetime
from odoo import fields, http
from odoo.http import request
from odoo.tools.misc import get_lang
from odoo.addons.appointment_booking_ce.controllers.main import WebsiteCalendar

_logger = logging.getLogger(__name__)


class GoogleMeetWebsiteCalendar(WebsiteCalendar):
    """Extend Zehntech WebsiteCalendar for Google Meet integration"""

    def _create_event(self, request, user, data):
        """Override event creation to handle Google Meet integration"""
        _logger.info("_create_event called with data: %s", data)

        booking_type_id = data.get('booking_type_id')
        booking_type = None

        if booking_type_id:
            booking_type = request.env['calendar.booking.type'].sudo().browse(
                booking_type_id
            )
            _logger.info("Booking type found: %s", booking_type.name)

            should_use_meet = booking_type._should_use_google_meet()
            _logger.info("Should use Google Meet: %s", should_use_meet)

            if should_use_meet:
                original_meeting_url = data.get('meeting_url', '')
                data['meeting_url'] = 'GOOGLE_MEET_PLACEHOLDER'
                _logger.info(
                    "Set placeholder, original was: %s", original_meeting_url
                )

        event = super()._create_event(request, user, data)
        _logger.info("Event created with ID: %s", event.id)

        if booking_type and booking_type._should_use_google_meet():
            _logger.info(
                "Attempting to generate Google Meet for event %s", event.id
            )
            try:
                meet_link = event._generate_google_meet_link()
                _logger.info("Google Meet generation result: %s", meet_link)

                if meet_link:
                    _logger.info("Writing Google Meet URL to event fields")
                    event.write({
                        'google_meet_url': meet_link,
                        'meeting_url': meet_link,
                        'videocall_location': meet_link,
                    })

                    event.refresh()
                    _logger.info(
                        "After write - videocall_location: %s",
                        event.videocall_location
                    )
                    _logger.info(
                        "After write - meeting_url: %s", event.meeting_url
                    )

                    booking_type.sudo().write({
                        'meeting_base_url': meet_link
                    })

                    _logger.info(
                        "Successfully set Google Meet URL: %s", meet_link
                    )
                else:
                    _logger.error("Failed to generate Google Meet link")
                    event.meeting_url = original_meeting_url

            except Exception as e:
                _logger.error("Exception generating Google Meet: %s", str(e))
                event.meeting_url = original_meeting_url

        return event

    @http.route(['/website/calendar/view/<string:access_token>'],
                type='http', auth="public", website=True)
    def calendar_booking_view(self, access_token, edit_token=None, **kwargs):
        """Override calendar booking view to fix timezone display"""

        result = super().calendar_booking_view(
            access_token, edit_token=edit_token, **kwargs
        )

        if not hasattr(result, 'qcontext'):
            return result

        event = result.qcontext.get('event')
        if not event:
            return result

        timezone = request.session.get('timezone')
        if not timezone:
            timezone = (
                request.env.context.get('tz') or
                event.booking_type_id.booking_tz or
                (event.partner_ids and event.partner_ids[0].tz) or
                event.appointment_user_id.tz or
                'UTC'
            )
            request.session['timezone'] = timezone

        tz_session = pytz.timezone(timezone)

        if not event.allday:
            date_start = fields.Datetime.from_string(event.start).replace(
                tzinfo=pytz.utc
            )

            date_start_local = date_start.astimezone(tz_session)

            locale = get_lang(request.env).code
            day_name = format_datetime(
                date_start_local, 'EEE', locale=locale
            )
            date_start_formatted = (
                day_name + ' ' +
                format_datetime(date_start_local, locale=locale)
            )

            result.qcontext.update({'datetime_start': date_start_formatted})

        return result

    @http.route([
        '/website/calendar/<model("calendar.booking.type"):booking_type>/'
        'submit'
    ], type='http', auth="public", website=True, methods=["POST"])
    def calendar_booking_submit(self, booking_type, **kwargs):
        """Override calendar booking for Google Meet integration"""

        booking_type_sudo = booking_type.sudo()
        use_google_meet = booking_type_sudo._should_use_google_meet()

        start_datetime_str = kwargs.get('start_datetime_str')
        if start_datetime_str:

            import pytz
            from datetime import datetime

            session_tz = request.session.get('timezone', 'UTC')
            session_timezone = pytz.timezone(session_tz)

            naive_dt = datetime.strptime(
                start_datetime_str, '%Y-%m-%d %H:%M:%S'
            )
            localized_dt = session_timezone.localize(naive_dt)

            utc_dt = localized_dt.astimezone(pytz.UTC)

            kwargs['start_datetime_str'] = utc_dt.strftime(
                '%Y-%m-%d %H:%M:%S'
            )

        if use_google_meet:

            result = super().calendar_booking_submit(booking_type, **kwargs)

            if (hasattr(result, 'location') and
                    '/website/calendar/view/' in result.location):
                try:

                    parts = result.location.split('/website/calendar/view/')[1]
                    access_token = parts.split('?')[0]
                    event = request.env['calendar.event'].sudo().search([
                        ('access_token', '=', access_token)
                    ], limit=1)

                    if (event and
                            event.booking_type_id._should_use_google_meet()):

                        if not event.google_meet_url:
                            meet_link = event._generate_google_meet_link()
                            if meet_link:
                                event.write({
                                    'videocall_location': meet_link,
                                    'meeting_url': meet_link,
                                })
                        else:

                            event.write({
                                'videocall_location': event.google_meet_url,
                                'meeting_url': event.google_meet_url,
                            })

                except Exception:
                    pass

            return result
        else:

            return super().calendar_booking_submit(booking_type, **kwargs)

    def _send_appointment_confirmation_email(self, event):
        """Send appointment confirmation email with custom template"""

        if (event.booking_type_id and
                event.booking_type_id._should_use_google_meet() and
                hasattr(event, 'google_meet_url') and event.google_meet_url):

            try:
                module = 'appointment_google_meet_integration'
                template_name = (
                    'google_meet_appointment_booking_'
                    'confirmation_mail_template'
                )
                template_ref = f'{module}.{template_name}'
                template = event.env.ref(template_ref)
                template.send_mail(event.id, force_send=True)
                return True
            except Exception:

                pass

        try:
            template = event.env.ref(
                'appointment_booking_ce.'
                'appointment_booking_confirmation_mail_template'
            )
            template.send_mail(event.id, force_send=True)
            return True
        except Exception:
            return False

    @http.route('/google_meet_authentication', type='http', auth='public',
                website=True)
    def google_meet_oauth_callback(self, **kwargs):
        """Handle Google OAuth callback for Meet integration"""
        code = kwargs.get('code')
        error = kwargs.get('error')

        if error:
            return request.redirect('/web?auth_error=authorization_failed')

        if not code:
            return request.redirect('/web?auth_error=no_code')

        try:

            config_param = request.env['ir.config_parameter'].sudo()
            client_id = config_param.get_param('google_meet.client_id')
            client_secret = config_param.get_param('google_meet.client_secret')
            redirect_uri = self._get_redirect_uri()

            if not client_id or not client_secret:
                return request.redirect('/web?google_meet_auth=missing_config')

            data = {
                'code': code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code'
            }

            import requests
            response = requests.post(
                'https://oauth2.googleapis.com/token',
                data=data,
                headers={'content-type': 'application/x-www-form-urlencoded'},
                timeout=30
            )

            if response.status_code == 200:
                token_data = response.json()
                if token_data.get('refresh_token'):

                    request.env['ir.config_parameter'].sudo().set_param(
                        'google_meet.refresh_token',
                        token_data['refresh_token']
                    )
                    return request.redirect('/web?google_meet_auth=success')
                else:
                    return request.redirect('/web?google_meet_auth=no_token')
            else:
                return request.redirect('/web?google_meet_auth=failed')

        except Exception:
            return request.redirect('/web?google_meet_auth=error')

    def _get_redirect_uri(self):
        """Get OAuth redirect URI"""
        base_url = request.env['ir.config_parameter'].sudo().get_param(
            'web.base.url'
        )
        return f"{base_url}/google_meet_authentication"
