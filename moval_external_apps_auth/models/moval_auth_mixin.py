# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
import time
import logging
from odoo import models, api, exceptions, _

try:
    import urllib2 as _urlreq
    from urllib import urlencode as _urlencode
    from urlparse import parse_qsl as _parse_qsl
    from urlparse import urlsplit as _urlsplit
    from urlparse import urlunsplit as _urlunsplit
    from cgi import escape as _html_escape
except ImportError:
    import urllib.request as _urlreq
    from urllib.parse import urlencode as _urlencode
    from urllib.parse import parse_qsl as _parse_qsl
    from urllib.parse import urlsplit as _urlsplit
    from urllib.parse import urlunsplit as _urlunsplit
    from html import escape as _html_escape

_logger = logging.getLogger(__name__)

_TOKEN_CACHE = {}

try:
    _text_type = unicode
except NameError:
    _text_type = str


def _query_value(value):
    if _text_type is not str and isinstance(value, _text_type):
        return value.encode("utf-8")
    return str(value)


class MovalAuthMixin(models.AbstractModel):
    _name = "moval.auth.mixin"
    _description = "Moval: shared auth methods for external app modules"

    @api.model
    def _get_system_config(self, key):
        return (self.env["ir.values"].sudo().get_default(
            "moval.auth.config", key) or "")

    @api.model
    def _get_service_token(self, client_id, client_secret):
        """Password grant against Keycloak using the instance's service account.

        Returns a JWT (access_token string). The cache is isolated by Odoo
        database, Keycloak endpoint, service user and client id.
        """
        token_url = self._get_system_config("moval_keycloak_token_url")
        username = self._get_system_config("moval_service_username")
        password = self._get_system_config("moval_service_password")

        if not (token_url and username and password and client_id):
            raise exceptions.ValidationError(
                _("External app auth not configured: need token_url, "
                  "service username/password, and client_id/client_secret."))

        cache_key = (
            self.env.cr.dbname, token_url, username, client_id or "_default")
        now = time.time()
        cached = _TOKEN_CACHE.get(cache_key)
        if cached and cached.get("exp", 0) - now > 15:
            return cached["jwt"]

        data = _urlencode({
            "grant_type": "password",
            "client_id": client_id,
            "client_secret": client_secret or "",
            "username": username,
            "password": password,
        })

        req = _urlreq.Request(token_url, data=data)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            resp = _urlreq.urlopen(req, timeout=10)
            payload = json.loads(resp.read())
        except Exception as exc:
            _logger.warning("Moval auth: token request failed: %s", exc)
            raise exceptions.ValidationError(
                _("Could not obtain service token from Keycloak: %s") % exc)

        jwt = payload.get("access_token")
        if not jwt:
            raise exceptions.ValidationError(
                _("Keycloak did not return access_token: %s") % (
                    payload.get("error_description") or
                    payload.get("error") or "unknown error"))

        expires_in = int(payload.get("expires_in") or 60)
        _TOKEN_CACHE[cache_key] = {
            "jwt": jwt,
            "exp": now + min(expires_in, 3600),
        }
        return jwt

    @api.model
    def _issue_ticket(self, jwt, acting_user, app_slug):
        """Create an opaque, single-use ticket for the given app."""
        return self.env["moval.service.ticket"].sudo().issue(
            jwt, acting_user, app_slug, ttl_seconds=30)

    @api.model
    def _append_query_params(self, url, params):
        parts = list(_urlsplit(url or ""))
        if parts[0].lower() not in ("http", "https") or not parts[1]:
            raise exceptions.ValidationError(
                _("External app URL must be an absolute HTTP(S) URL."))
        query = _parse_qsl(parts[3], keep_blank_values=True)
        query.extend((_query_value(key), _query_value(value))
                     for key, value in params)
        parts[3] = _urlencode(query)
        return _urlunsplit(parts)

    @api.model
    def _get_app_url_with_ticket(self, app_slug, extra_params=None):
        """Return the external app URL with a fresh single-use ?ticket=.

        Shared by the embedded iframe and the "open in new tab" action.
        Falls back to the bare app URL if token/ticket issuance fails.
        Returns an empty string if the app is not registered or has no URL.
        """
        app = self.env["moval.external.app"].sudo().search(
            [("slug", "=", app_slug), ("active", "=", True)], limit=1)
        if not app:
            return ""

        url = app.app_url or ""
        if not url:
            return ""

        try:
            jwt = self._get_service_token(
                app.keycloak_client_id, app.keycloak_client_secret)
            acting_user = (self.env.user.login if self.env.user else "")
            ticket = self._issue_ticket(jwt, acting_user, app_slug)
            params = [("ticket", ticket)]
            params.extend((extra_params or {}).items())
            url = self._append_query_params(url, params)
        except Exception as exc:
            _logger.warning("Moval auth: url ticket failed for %s: %s",
                            app_slug, exc)
            return ""
        return url

    @api.model
    def _build_iframe(self, app_slug, extra_params=None):
        """Build an <iframe> tag with ?ticket= for the given external app.

        App-specific modules call this with their slug. Returns HTML string.
        """
        app = self.env["moval.external.app"].sudo().search(
            [("slug", "=", app_slug), ("active", "=", True)], limit=1)
        if not app:
            message = _("External app '%s' is not registered.") % app_slug
            return "<div class='alert alert-warning'>%s</div>" % (
                _html_escape(message, quote=True))
        url = app.app_url or ""
        if not url:
            message = _("App URL not set for '%s'.") % app_slug
            return "<div class='alert alert-warning'>%s</div>" % (
                _html_escape(message, quote=True))

        src = self._get_app_url_with_ticket(app_slug, extra_params=extra_params)
        if not src:
            message = _("Could not authenticate against external app '%s'.") % (
                app_slug)
            return "<div class='alert alert-danger'>%s</div>" % (
                _html_escape(message, quote=True))

        return (
            '<iframe id="moval_%s_frame" marginwidth="0" '
            'marginheight="0" frameborder="no" '
            'width="100%%" height="100%%" '
            'allow="clipboard-read; clipboard-write; fullscreen" '
            'sandbox="allow-scripts allow-same-origin allow-forms '
            'allow-downloads allow-popups" '
            'referrerpolicy="strict-origin-when-cross-origin" '
            'src="%s">'
            '</iframe>'
        ) % (_html_escape(app_slug, quote=True),
             _html_escape(src, quote=True))
