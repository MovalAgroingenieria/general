# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import json
import hmac

from odoo import http
from odoo.http import request
from odoo.modules.registry import RegistryManager
from odoo.api import Environment
from werkzeug.wrappers import Response

_logger = logging.getLogger(__name__)


class MovalAuthController(http.Controller):

    @http.route(
        "/moval/redeem-ticket",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False)
    def redeem_ticket(self, **kwargs):
        def _json(code, payload):
            return Response(
                json.dumps(payload),
                status=code,
                content_type="application/json")

        try:
            raw = request.httprequest.get_data(as_text=True) or "{}"
            body = json.loads(raw) if raw else {}
        except Exception:
            return _json(400, {"error": "invalid json body"})

        db = body.get("db") or request.db
        ticket = body.get("ticket")
        app_slug = body.get("app_slug")
        presented = self._get_bearer_secret()

        if not (db and ticket and app_slug and presented):
            return _json(401, {"error": "unauthorized"})

        try:
            registry = RegistryManager.get(db)
        except Exception as exc:
            _logger.warning("Moval redeem: registry %s failed: %s", db, exc)
            return _json(401, {"error": "unauthorized"})

        cr = None
        try:
            cr = registry.cursor()
            env = Environment(cr, 1, {})

            app = env["moval.external.app"].search(
                [("slug", "=", app_slug), ("active", "=", True)], limit=1)
            if not app:
                _logger.warning(
                    "Moval redeem: unknown app_slug=%s", app_slug)
                return _json(401, {"error": "unauthorized"})

            expected = app.app_shared_secret or ""
            if not expected or not hmac.compare_digest(
                    str(expected), str(presented)):
                _logger.warning(
                    "Moval redeem: shared secret mismatch for app=%s", app_slug)
                return _json(401, {"error": "unauthorized"})

            result = env["moval.service.ticket"].redeem(ticket, app_slug)
            if not result:
                cr.rollback()
                return _json(401, {"error": "invalid or expired ticket"})

            cr.commit()
            pg_host = None
            pg_port = None
            try:
                values = env["ir.values"].sudo()
                pg_host = values.get_default(
                    "moval.auth.config", "moval_external_pg_host") or None
                pg_port_raw = values.get_default(
                    "moval.auth.config", "moval_external_pg_port")
                pg_port = int(pg_port_raw) if pg_host and pg_port_raw else None
            except (TypeError, ValueError):
                _logger.warning(
                    "Moval redeem: invalid external PostgreSQL port for db=%s",
                    db)
            return _json(200, {
                "jwt": result["jwt"],
                "acting_user": result.get("acting_user", ""),
                "app_slug": result.get("app_slug", ""),
                "db_name": db,
                "pg_host": pg_host,
                "pg_port": pg_port,
                "pg_database": db,
            })
        finally:
            if cr is not None:
                cr.close()

    @staticmethod
    def _get_bearer_secret():
        auth = (request.httprequest.headers.get("Authorization") or "")
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return ""
