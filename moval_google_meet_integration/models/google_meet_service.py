# Copyright 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from datetime import datetime

from odoo import api, models, _
from odoo.exceptions import UserError

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
except ImportError:
    logging.getLogger(__name__).warning(
        "Google APIs not installed. Run: pip install "
        "google-auth google-auth-oauthlib google-auth-httplib2 "
        "google-api-python-client"
    )

_logger = logging.getLogger(__name__)


class GoogleMeetService(models.AbstractModel):
    _name = 'google.meet.service'
    _description = 'Google Meet API Service'

    @api.model
    def get_authorization_url(self, client_id, client_secret):
        """Generate Google OAuth authorization URL"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self._get_redirect_uri()]
                }
            },
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        flow.redirect_uri = self._get_redirect_uri()

        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return auth_url

    @api.model
    def _get_redirect_uri(self):
        """Get OAuth redirect URI"""
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url'
        )
        return f"{base_url}/google_meet_authentication"

    @api.model
    def exchange_code_for_token(self, code, client_id, client_secret):
        """Exchange authorization code for access token"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self._get_redirect_uri()]
                }
            },
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        flow.redirect_uri = self._get_redirect_uri()

        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Store refresh token
        self.env['ir.config_parameter'].sudo().set_param(
            'google_meet.refresh_token',
            credentials.refresh_token
        )

        return credentials.refresh_token

    @api.model
    def _get_credentials(self):
        """Get Google credentials from stored tokens"""
        config = self.env['res.config.settings'].get_google_meet_config()

        if not all([
            config.get('client_id'),
            config.get('client_secret'),
            config.get('refresh_token')
        ]):
            raise UserError(_(
                "Google Meet integration not properly configured. "
                "Please complete the OAuth setup."
            ))

        credentials = Credentials(
            token=None,
            refresh_token=config['refresh_token'],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=config['client_id'],
            client_secret=config['client_secret'],
            scopes=['https://www.googleapis.com/auth/calendar']
        )

        # Refresh the token if needed
        if not credentials.valid:
            credentials.refresh(Request())

        return credentials

    @api.model
    def test_connection(self):
        """Test Google Calendar API connection"""
        try:
            credentials = self._get_credentials()
            service = build('calendar', 'v3', credentials=credentials)

            # Simple API call to test connection
            service.calendarList().list(maxResults=1).execute()
            return True

        except Exception as e:
            _logger.error(f"Google Meet connection test failed: {e}")
            raise UserError(_(
                "Connection test failed: %s"
            ) % str(e))

    @api.model
    def create_meet_event(self, event_data):
        """Create Google Calendar event with Meet link

        Args:
            event_data (dict): Event information with keys:
                - summary: Event title
                - description: Event description
                - start_datetime: Start datetime (ISO format)
                - end_datetime: End datetime (ISO format)
                - attendees: List of attendee emails
                - calendar_id: Google Calendar ID (optional)

        Returns:
            dict: Event data including meet link
        """
        try:
            credentials = self._get_credentials()
            service = build('calendar', 'v3', credentials=credentials)

            # Get calendar ID (default to primary)
            calendar_id = event_data.get('calendar_id', 'primary')

            # Prepare event body
            event_body = {
                'summary': event_data.get('summary', 'Appointment'),
                'description': event_data.get('description', ''),
                'start': {
                    'dateTime': event_data['start_datetime'],
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': event_data['end_datetime'],
                    'timeZone': 'UTC',
                },
                'conferenceData': {
                    'createRequest': {
                        'requestId': f"meet-{datetime.now().timestamp()}",
                        'conferenceSolutionKey': {
                            'type': 'hangoutsMeet'
                        }
                    }
                },
                'attendees': [
                    {'email': email}
                    for email in event_data.get('attendees', [])
                ],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day
                        {'method': 'popup', 'minutes': 30},       # 30 min
                    ],
                },
            }

            # Create the event
            created_event = service.events().insert(
                calendarId=calendar_id,
                body=event_body,
                conferenceDataVersion=1,
                sendUpdates='none'  # Don't send Google invitations
            ).execute()

            # Extract Meet link
            meet_link = None
            if 'conferenceData' in created_event:
                meet_link = created_event['conferenceData'].get(
                    'entryPoints', [{}]
                )[0].get('uri')

            return {
                'google_event_id': created_event['id'],
                'meet_link': meet_link,
                'event_url': created_event.get('htmlLink'),
                'success': True
            }

        except Exception as e:
            _logger.error(f"Failed to create Google Meet event: {e}")
            raise UserError(_(
                "Failed to create Google Meet event: %s"
            ) % str(e))

    @api.model
    def update_meet_event(self, google_event_id, event_data, calendar_id='primary'):
        """Update existing Google Calendar event"""
        try:
            credentials = self._get_credentials()
            service = build('calendar', 'v3', credentials=credentials)

            # Get existing event
            existing_event = service.events().get(
                calendarId=calendar_id,
                eventId=google_event_id
            ).execute()

            # Update fields
            if 'summary' in event_data:
                existing_event['summary'] = event_data['summary']
            if 'description' in event_data:
                existing_event['description'] = event_data['description']
            if 'start_datetime' in event_data:
                existing_event['start'] = {
                    'dateTime': event_data['start_datetime'],
                    'timeZone': 'UTC'
                }
            if 'end_datetime' in event_data:
                existing_event['end'] = {
                    'dateTime': event_data['end_datetime'],
                    'timeZone': 'UTC'
                }

            # Update the event
            updated_event = service.events().update(
                calendarId=calendar_id,
                eventId=google_event_id,
                body=existing_event,
                sendUpdates='none'
            ).execute()

            return {
                'success': True,
                'event_url': updated_event.get('htmlLink')
            }

        except Exception as e:
            _logger.error(f"Failed to update Google Meet event: {e}")
            return {'success': False, 'error': str(e)}

    @api.model
    def delete_meet_event(self, google_event_id, calendar_id='primary'):
        """Delete Google Calendar event"""
        try:
            credentials = self._get_credentials()
            service = build('calendar', 'v3', credentials=credentials)

            service.events().delete(
                calendarId=calendar_id,
                eventId=google_event_id,
                sendUpdates='none'
            ).execute()

            return {'success': True}

        except Exception as e:
            _logger.error(f"Failed to delete Google Meet event: {e}")
            return {'success': False, 'error': str(e)}