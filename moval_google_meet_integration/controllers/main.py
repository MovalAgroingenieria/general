# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo import http
from odoo.http import request
from odoo.addons.appointment_booking_ce.controllers.main import WebsiteCalendar

_logger = logging.getLogger(__name__)


class GoogleMeetWebsiteCalendar(WebsiteCalendar):
    """Extend Zehntech WebsiteCalendar for Google Meet integration"""

    def _create_event(self, request, user, data):
        """Override event creation to handle Google Meet integration"""
        _logger.info("Creating event with Google Meet integration...")

        # Get booking type from data
        booking_type_id = data.get('booking_type_id')
        booking_type = None

        if booking_type_id:
            booking_type = request.env['calendar.booking.type'].sudo().browse(
                booking_type_id
            )
            _logger.info(f"Booking type: {booking_type.name}")
            _logger.info(
                f"Should use Google Meet: "
                f"{booking_type._should_use_google_meet()}"
            )

            # If should use Google Meet, temporarily modify data
            if booking_type._should_use_google_meet():
                # Store original meeting_url to restore if Google Meet fails
                original_meeting_url = data.get('meeting_url', '')
                data['meeting_url'] = 'GOOGLE_MEET_PLACEHOLDER'
                _logger.info("Set Google Meet placeholder")

        # Create the event using parent method
        event = super()._create_event(request, user, data)

        # If Google Meet is needed, generate it now
        if booking_type and booking_type._should_use_google_meet():
            try:
                _logger.info(f"Generating Google Meet for event {event.id}")
                meet_link = event._generate_google_meet_link()

                if meet_link:
                    _logger.info(f"Google Meet generated: {meet_link}")
                    # This will be the final meeting_url
                    event.google_meet_url = meet_link
                else:
                    _logger.error("Failed to generate Google Meet link")
                    # Restore original if generation failed
                    event.meeting_url = original_meeting_url

            except Exception as e:
                _logger.error(f"Error generating Google Meet: {e}")
                # Restore original meeting_url on error
                event.meeting_url = original_meeting_url

        return event

    @http.route([
        '/website/calendar/<model("calendar.booking.type"):booking_type>/'
        'submit'
    ], type='http', auth="public", website=True, methods=["POST"])
    def calendar_booking_submit(self, booking_type, **kwargs):
        """Override calendar booking for Google Meet integration"""
        _logger.info(f"Processing booking for: {booking_type.name}")

        # Call parent method which will use our _create_event override
        result = super().calendar_booking_submit(booking_type, **kwargs)

        # After parent method, videocall_location has been set
        # We need to find event and fix meeting_url if Google Meet
        if (hasattr(result, 'location') and
                '/website/calendar/view/' in result.location):
            try:
                # Extract access token from redirect URL
                parts = result.location.split('/website/calendar/view/')[1]
                access_token = parts.split('?')[0]
                event = request.env['calendar.event'].sudo().search([
                    ('access_token', '=', access_token)
                ], limit=1)

                if event and booking_type._should_use_google_meet():
                    if (hasattr(event, 'google_meet_url') and
                            event.google_meet_url):
                        # Restore Google Meet URL that was overwritten
                        _logger.info(
                            f"Restoring Google Meet: {event.google_meet_url}"
                        )
                        event.write({'meeting_url': event.google_meet_url})
                        _logger.info("Google Meet URL restored successfully")

            except Exception as e:
                _logger.error(f"Error restoring Google Meet URL: {e}")

        return result

    @http.route('/google_meet_authentication', type='http', auth='public',
                website=True)
    def google_meet_oauth_callback(self, **kwargs):
        """Handle Google OAuth callback for Meet integration"""
        code = kwargs.get('code')
        error = kwargs.get('error')

        if error:
            _logger.error(f"OAuth authorization error: {error}")
            return request.redirect('/web?auth_error=authorization_failed')

        if not code:
            _logger.error("OAuth callback received without code")
            return request.redirect('/web?auth_error=no_code')

        try:
            # Exchange code for tokens
            config_param = request.env['ir.config_parameter'].sudo()
            client_id = config_param.get_param('google_meet.client_id')
            client_secret = config_param.get_param('google_meet.client_secret')
            redirect_uri = self._get_redirect_uri()

            _logger.info(f"OAuth token exchange - Code: {code[:20]}...")
            _logger.info(
                f"OAuth token exchange - Client ID: "
                f"{client_id[:20] if client_id else 'None'}..."
            )
            _logger.info(
                f"OAuth token exchange - Redirect URI: {redirect_uri}"
            )

            if not client_id or not client_secret:
                _logger.error("Missing Client ID or Client Secret")
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

            _logger.info(f"OAuth response status: {response.status_code}")
            if response.status_code != 200:
                _logger.error(f"OAuth response error: {response.text}")

            if response.status_code == 200:
                token_data = response.json()
                if token_data.get('refresh_token'):
                    # Save refresh token
                    request.env['ir.config_parameter'].sudo().set_param(
                        'google_meet.refresh_token',
                        token_data['refresh_token']
                    )
                    _logger.info("Google Meet authorization successful")
                    return request.redirect('/web?google_meet_auth=success')
                else:
                    _logger.error("No refresh token received")
                    return request.redirect('/web?google_meet_auth=no_token')
            else:
                _logger.error(f"Token exchange failed: {response.status_code}")
                return request.redirect('/web?google_meet_auth=failed')

        except Exception as e:
            _logger.error(f"OAuth callback error: {e}")
            return request.redirect('/web?google_meet_auth=error')

    def _get_redirect_uri(self):
        """Get OAuth redirect URI"""
        base_url = request.env['ir.config_parameter'].sudo().get_param(
            'web.base.url'
        )
        return f"{base_url}/google_meet_authentication"
