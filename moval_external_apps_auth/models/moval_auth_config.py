# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, exceptions, _


class MovalAuthConfig(models.TransientModel):
    _name = "moval.auth.config"
    _description = "Moval: system-level auth configuration for external apps"

    moval_keycloak_token_url = fields.Char(
        string="Keycloak Token URL",
        groups="base.group_system")

    moval_service_username = fields.Char(
        string="Service Username",
        groups="base.group_system")

    moval_service_password = fields.Char(
        string="Service Password",
        groups="base.group_system")

    moval_external_pg_host = fields.Char(
        string="External PostgreSQL Host",
        groups="base.group_system",
        help="Optional PostgreSQL host reachable from external applications. "
             "Leave empty when direct database access is not available.")

    moval_external_pg_port = fields.Integer(
        string="External PostgreSQL Port",
        groups="base.group_system",
        help="Port associated with the external PostgreSQL host.")

    def _default_token_url(self):
        return (self.env["ir.values"].sudo().get_default(
            "moval.auth.config", "moval_keycloak_token_url")
            or "https://auth.moval.es/realms/master/protocol/"
               "openid-connect/token")

    def _default_service_username(self):
        return (self.env["ir.values"].sudo().get_default(
            "moval.auth.config", "moval_service_username") or "")

    def _default_service_password(self):
        return (self.env["ir.values"].sudo().get_default(
            "moval.auth.config", "moval_service_password") or "")

    def _default_external_pg_host(self):
        return (self.env["ir.values"].sudo().get_default(
            "moval.auth.config", "moval_external_pg_host") or "")

    def _default_external_pg_port(self):
        return int(self.env["ir.values"].sudo().get_default(
            "moval.auth.config", "moval_external_pg_port") or 0)

    @api.model
    def default_get(self, fields_list):
        self._check_system_admin()
        res = super(MovalAuthConfig, self).default_get(fields_list)
        for fname in fields_list:
            if hasattr(self, "_default_" + fname):
                res.setdefault(fname, getattr(self, "_default_" + fname)())
        return res

    @api.multi
    def set_default_values(self):
        self._check_system_admin()
        values = self.env["ir.values"].sudo()
        for fname in ("moval_keycloak_token_url",
                       "moval_service_username",
                       "moval_service_password",
                       "moval_external_pg_host",
                       "moval_external_pg_port"):
            values.set_default("moval.auth.config", fname, getattr(self, fname))

    @api.model
    def _check_system_admin(self):
        if not self.env.user.has_group("base.group_system"):
            raise exceptions.AccessError(
                _("Only Odoo administrators can manage external app auth."))
