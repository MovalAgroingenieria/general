# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import os
from datetime import datetime, timedelta
from odoo import models, fields, api


class MovalServiceTicket(models.TransientModel):
    _name = "moval.service.ticket"
    _description = "Moval: opaque service ticket for external app auth (single-use)"

    ticket = fields.Char(index=True, required=True)
    jwt = fields.Text(required=True)
    acting_user = fields.Char()
    app_slug = fields.Char(index=True)
    create_date = fields.Datetime(readonly=True)
    expires_at = fields.Datetime(required=True)

    _sql_constraints = [
        ("ticket_uniq", "unique(ticket)", "Service ticket must be unique."),
    ]

    @api.model
    def _gc_expired(self):
        now = fields.Datetime.now()
        self.search([("expires_at", "<", now)]).unlink()

    @api.model
    def issue(self, jwt, acting_user, app_slug, ttl_seconds=30):
        self._gc_expired()
        raw = base64.b16encode(os.urandom(32)).decode("ascii").lower()
        ticket = "moval_" + raw
        expires_at = fields.Datetime.to_string(
            datetime.utcnow() + timedelta(seconds=ttl_seconds))
        self.create({
            "ticket": ticket,
            "jwt": jwt,
            "acting_user": acting_user or "",
            "app_slug": app_slug or "",
            "expires_at": expires_at,
        })
        return ticket

    @api.model
    def redeem(self, ticket, app_slug=None):
        self._gc_expired()
        now = fields.Datetime.now()
        query = (
            "SELECT id FROM %s "
            "WHERE ticket = %%s AND expires_at >= %%s" % self._table)
        params = [ticket, now]
        if app_slug:
            query += " AND app_slug = %s"
            params.append(app_slug)
        query += " FOR UPDATE"
        self.env.cr.execute(query, params)
        row = self.env.cr.fetchone()
        if not row:
            return None
        rec = self.browse(row[0])
        payload = {
            "jwt": rec.jwt,
            "acting_user": rec.acting_user or "",
            "app_slug": rec.app_slug or "",
        }
        rec.unlink()
        return payload
