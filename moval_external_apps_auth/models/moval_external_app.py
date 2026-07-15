# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class MovalExternalApp(models.Model):
    _name = "moval.external.app"
    _description = "Moval: registry of external apps embeddable in Odoo"

    name = fields.Char(string="App Name", required=True, translate=True)
    slug = fields.Char(string="Slug", required=True, index=True,
                       help="Short identifier, e.g. 'balances-hidricos', 'telecontrol'")
    app_url = fields.Char(string="App URL", required=True,
                          help="Base URL of the external app, e.g. "
                               "https://balances-hidricos.moval-ia.es")
    keycloak_client_id = fields.Char(
        string="Keycloak Client ID",
        help="OIDC client id for this app in Keycloak, e.g. 'balances-hidricos'")
    keycloak_client_secret = fields.Char(
        string="Keycloak Client Secret", password="True",
        groups="base.group_system",
        help="Secret of the OIDC client (from Keycloak client Credentials tab)")
    app_shared_secret = fields.Char(
        string="App Shared Secret", password="True",
        groups="base.group_system",
        help="Shared secret for the app <-> Odoo redeem channel. "
             "Must match the external app's Odoo shared-secret setting.")
    active = fields.Boolean(default=True)

    client_launcher_model = fields.Char(
        string="Launcher model (technical)",
        help="Technical name of this app's launcher model in this Odoo "
             "instance, e.g. 'hydric.balance.manager'. Set automatically "
             "by the app module on install.")
    client_menu_xmlids = fields.Char(
        string="Launcher menu external IDs",
        help="Comma-separated full external IDs (module.xmlid) of the "
             "launcher menuitems to hide/show for base.group_user, e.g. "
             "'wua_hydric_balance_manager.hydric_balance_manager_menu'.")

    _sql_constraints = [
        ("slug_uniq", "unique(slug)", "Slug must be unique."),
    ]

    @api.multi
    def name_get(self):
        return [(r.id, "%s (%s)" % (r.name, r.slug)) for r in self]

    def _sync_client_access(self):
        """Grant or revoke base.group_user access to this app's launcher
        model and menu items, based on the active flag.
        """
        group_user = self.env.ref("base.group_user")
        group_system = self.env.ref("base.group_system")

        for app in self:
            enabled = app.active
            if app.client_launcher_model:
                model = self.env["ir.model"].search(
                    [("model", "=", app.client_launcher_model)], limit=1)
                if model:
                    access = self.env["ir.model.access"].search([
                        ("model_id", "=", model.id),
                        ("group_id", "=", group_user.id),
                    ], limit=1)
                    values = {
                        "name": "%s.client_access" % app.client_launcher_model,
                        "model_id": model.id,
                        "group_id": group_user.id,
                        "perm_read": enabled,
                        "perm_write": enabled,
                        "perm_create": enabled,
                        "perm_unlink": enabled,
                    }
                    if access:
                        access.write(values)
                    else:
                        self.env["ir.model.access"].create(values)

            if app.client_menu_xmlids:
                xmlids = [x.strip() for x in app.client_menu_xmlids.split(",")
                          if x.strip()]
                group_ids = [group_system.id]
                if enabled:
                    group_ids.append(group_user.id)
                for xmlid in xmlids:
                    menu = self.env.ref(xmlid, raise_if_not_found=False)
                    if menu:
                        menu.write({"groups_id": [(6, 0, group_ids)]})
        return True

    @api.model
    def create(self, vals):
        record = super(MovalExternalApp, self).create(vals)
        record._sync_client_access()
        return record

    @api.multi
    def write(self, vals):
        result = super(MovalExternalApp, self).write(vals)
        if "active" in vals or "client_launcher_model" in vals \
                or "client_menu_xmlids" in vals:
            self._sync_client_access()
        return result
