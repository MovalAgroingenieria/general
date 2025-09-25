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

    @http.route('/google_meet/oauth/callback', type='http', auth='public')
    def google_meet_oauth_callback(self, **kwargs):
        """Handle Google OAuth callback for Meet integration"""
        code = kwargs.get('code')
        error = kwargs.get('error')

        if error:
            return request.render('web.login', {
                'error': f"Google authorization failed: {error}"
            })

        if not code:
            return request.render('web.login', {
                'error': "No authorization code received from Google"
            })

        try:
            # Exchange code for tokens
            config = request.env['res.config.settings'].get_google_meet_config()
            google_service = request.env['google.meet.service']

            refresh_token = google_service.exchange_code_for_token(
                code,
                config['client_id'],
                config['client_secret']
            )

            if refresh_token:
                # Test the connection
                if google_service.test_connection():
                    message = "Google Meet integration authorized successfully!"
                    success = True
                else:
                    message = "Authorization successful but connection test failed"
                    success = False
            else:
                message = "Failed to obtain refresh token"
                success = False

        except Exception as e:
            _logger.error(f"OAuth callback error: {e}")
            message = f"Authorization failed: {str(e)}"
            success = False

        # Redirect back to settings with result
        return request.redirect(
            f'/web#action=base.action_res_config_settings'
            f'&message={message}&success={success}'
        )