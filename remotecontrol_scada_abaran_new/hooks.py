# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


def uninstall_hook(cr, registry):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    remote = env.ref(
        'remotecontrol_scada_abaran_new.remotecontrol_scada_abaran_new',
        raise_if_not_found=False,
    )
    if remote:
        remote.with_context(force_unlink=True).unlink()
