# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    remote = env.ref(
        'remotecontrol_saih_ebro.remotecontrol_saih_ebro',
        raise_if_not_found=False,
    )
    if remote:
        remote.with_context(force_unlink=True).unlink()
