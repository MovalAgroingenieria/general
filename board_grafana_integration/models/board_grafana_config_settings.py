# -*- coding: utf-8 -*-
# 2022 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import logging

from odoo import api, exceptions, fields, models, _

_logger = logging.getLogger(__name__)

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
except ImportError:
    _logger.debug('Cannot import cryptography')


class BoardGrafanaConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    _name = "board.grafana.configuration"

    PARAM_JWT_PRIVATE_KEY = 'board_grafana_integration.jwt_private_key'
    JWT_ISSUER = 'odoo'
    JWT_KEY_SIZE = 2048

    grafana_url_raw = fields.Char(
        string="Grafana URL",
        required=True,
        help="The URL of grafana host.")

    grafana_url = fields.Char(
        compute="_compute_grafana_url")

    grafana_api_key = fields.Char(
        string="Grafana API Key")

    grafana_default_datasource = fields.Char(
        string="Default datasource",
        help="The default datasource.")

    grafana_dashboard_height = fields.Integer(
        string="Dashboard height",
        help="Height of dashboard, in pixels (optional).")

    grafana_dashboard_uid = fields.Char(
        string="Dashboard uid",
        help="The id of the welcome dashboard "
             "(optional, else the dashboard list will be shown).")

    grafana_show_navbar_button = fields.Boolean(
        string="Show navbar button",
        default=False,
        help="Show the Grafana button in the top navigation bar, which "
             "opens Grafana in a side panel.",
    )

    grafana_jwt_login = fields.Char(
        string="Grafana user",
        help="Login of the Grafana user (e.g. odooreader) that Odoo users "
             "are signed in as with a JWT. It must exist in Grafana with "
             "the Viewer role. Leave empty to disable the automatic login.",
    )

    grafana_jwt_key_value = fields.Text(
        string="JWT public key",
        readonly=True,
        help="Value of the 'key_value' setting of the [auth.jwt] section of "
             "grafana.ini, so that Grafana accepts the JWT signed by Odoo. "
             "The RSA key pair is generated when the settings are applied; "
             "the private key never leaves Odoo.",
    )

    @api.depends("grafana_url_raw")
    def _compute_grafana_url(self):
        for record in self:
            url = record.grafana_url_raw
            if url.endswith("/"):
                url = url.rstrip("/")
            record.grafana_url = url

    @api.model
    def get_default_grafana_jwt_key_value(self, fields):
        return {'grafana_jwt_key_value': self._get_grafana_jwt_key_value()}

    @api.multi
    def set_default_values(self):
        values = self.env["ir.values"].sudo()
        values.set_default("board.grafana.configuration",
                           "grafana_url_raw", self.grafana_url_raw)
        values.set_default("board.grafana.configuration",
                           "grafana_url", self.grafana_url)
        values.set_default("board.grafana.configuration",
                           "grafana_api_key", self.grafana_api_key)
        values.set_default("board.grafana.configuration",
                           "grafana_default_datasource",
                           self.grafana_default_datasource)
        values.set_default("board.grafana.configuration",
                           "grafana_dashboard_height",
                           self.grafana_dashboard_height)
        values.set_default("board.grafana.configuration",
                           "grafana_dashboard_uid",
                           self.grafana_dashboard_uid)
        values.set_default("board.grafana.configuration",
                           "grafana_show_navbar_button",
                           self.grafana_show_navbar_button)
        values.set_default("board.grafana.configuration",
                           "grafana_jwt_login",
                           (self.grafana_jwt_login or "").strip())

    @api.multi
    def set_grafana_jwt_config(self):
        if (self.grafana_jwt_login or "").strip() and \
                not self._get_grafana_jwt_private_key():
            self._generate_grafana_jwt_private_key()

    @api.multi
    def action_generate_grafana_jwt_key(self):
        if not self.env.user._is_superuser() and \
                not self.env.user.has_group('base.group_system'):
            raise exceptions.AccessError(
                _("Only administrators can change the settings"))
        self._generate_grafana_jwt_private_key()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.model
    def _get_grafana_jwt_login(self):
        login = self.env["ir.values"].get_default(
            "board.grafana.configuration", "grafana_jwt_login")
        return (login or "").strip()

    @api.model
    def _get_grafana_jwt_private_key(self):
        # Private on purpose: the key must never reach the browser
        pem = self.env['ir.config_parameter'].sudo().get_param(
            self.PARAM_JWT_PRIVATE_KEY)
        private_key = False
        if pem:
            private_key = serialization.load_pem_private_key(
                pem.encode('ascii'), password=None, backend=default_backend())
        return private_key

    @api.model
    def _generate_grafana_jwt_private_key(self):
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=self.JWT_KEY_SIZE,
            backend=default_backend())
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption())
        # Hidden from the ir.config_parameter read rule of other users
        self.env['ir.config_parameter'].sudo().set_param(
            self.PARAM_JWT_PRIVATE_KEY, pem, groups=['base.group_system'])
        return private_key

    @api.model
    def _get_grafana_jwt_key_value(self):
        private_key = self._get_grafana_jwt_private_key()
        key_value = False
        if self._get_grafana_jwt_login() and private_key:
            public_pem = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo)
            key_value = base64.b64encode(public_pem)
        return key_value
