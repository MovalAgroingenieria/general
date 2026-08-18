# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from odoo import api, SUPERUSER_ID, _, exceptions


_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """Register this app in moval.external.app if it does not exist yet.

    Runs once at install time. A hook is used instead of XML seed data
    with noupdate so that credentials configured after install are never
    overwritten by a subsequent module update.
    """

    env = api.Environment(cr, SUPERUSER_ID, {})
    app = env["moval.external.app"].search([
        ("slug", "=", "modificar-comunicacion-remesas")])
    launcher_fields = {
        "client_launcher_model":
            "account.modify.payment.batches.communication",
        "client_menu_xmlids": (
            "account_modify_payment_batches_communication_menu",
        ),
    }
    if not app:
        env["moval.external.app"].create(dict({
            "name": "Modificar Comunicación Remesas",
            "slug": "modificar-comunicacion-remesas",
            "app_url": "https://comunicacion-remesa.moval-ia.es",
            "keycloak_client_id": "modificar-comunicacion-remesas",
            "active": True,
        }, **launcher_fields))
    else:
        values = {}
        for field_name, value in launcher_fields.items():
            if getattr(app, field_name) != value:
                values[field_name] = value
        if values:
            app.write(values)
        app._sync_client_access()
