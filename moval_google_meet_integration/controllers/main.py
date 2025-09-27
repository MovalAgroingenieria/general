# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo import http
from odoo.http import request
from odoo.addons.appointment_booking_ce.controllers.main import WebsiteCalendar

_logger = logging.getLogger(__name__)


class GoogleMeetWebsiteCalendar(WebsiteCalendar):
    """Extend Zehntech WebsiteCalendar controller for Google Meet integration"""

    @http.route(['/website/calendar/book'], type='json', auth="public",
                methods=['POST'], website=True)
    def calendar_book(self, **kwargs):
        """Override calendar booking to add Google Meet integration

        This method intercepts the booking process from Zehntech module
        and ensures Google Meet links are generated when enabled.
        """
        # Call parent method to create the appointment
        result = super().calendar_book(**kwargs)

        # Check if booking was successful and has event_id
        if not result or not result.get('event_id'):
            return result

        try:
            # Get the created event
            event = request.env['calendar.event'].sudo().browse(
                result['event_id']
            )

            # Check if this booking type should use Google Meet
            if (event.booking_type_id and
                event.booking_type_id._should_use_google_meet() and
                not event.google_meet_generated):

                # Generate Google Meet link if not already done
                meet_link = event._generate_google_meet_link()

                if meet_link:
                    # Update result with Google Meet link
                    result['meet_link'] = meet_link
                    result['google_meet_generated'] = True

                    _logger.info(
                        f"Google Meet link generated for booking {event.id}: "
                        f"{meet_link}"
                    )

        except Exception as e:
            _logger.error(f"Error in Google Meet integration: {e}")
            # Don't fail the booking if Google Meet generation fails
            pass

        return result

    @http.route('/google_meet_authentication', type='http', auth='public',
                website=True)
    def google_meet_oauth_callback(self, **kwargs):
        """Handle Google OAuth callback for Meet integration"""
        code = kwargs.get('code')
        error = kwargs.get('error')

        if error:
            return request.redirect('/web#action=base.action_res_config_settings&error=authorization_failed')

        if not code:
            return request.redirect('/web#action=base.action_res_config_settings&error=no_code')

        try:
            # Exchange code for tokens
            data = {
                'code': code,
                'client_id': request.env['ir.config_parameter'].sudo().get_param('google_meet.client_id'),
                'client_secret': request.env['ir.config_parameter'].sudo().get_param('google_meet.client_secret'),
                'redirect_uri': self._get_redirect_uri(),
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
                    # Save refresh token
                    request.env['ir.config_parameter'].sudo().set_param(
                        'google_meet.refresh_token',
                        token_data['refresh_token']
                    )
                    return request.redirect('/web#action=base.action_res_config_settings&success=authorized')
                else:
                    return request.redirect('/web#action=base.action_res_config_settings&error=no_refresh_token')
            else:
                return request.redirect('/web#action=base.action_res_config_settings&error=token_exchange_failed')

        except Exception as e:
            _logger.error(f"OAuth callback error: {e}")
            return request.redirect('/web#action=base.action_res_config_settings&error=exception')

    def _get_redirect_uri(self):
        """Get OAuth redirect URI"""
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/google_meet_authentication"