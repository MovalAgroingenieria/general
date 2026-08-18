# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # The "Spherag: Daily Sync" procedure is defined in a noupdate="1"
    # data block, so the newly added procedure_for_readings flag is not
    # applied to existing records on upgrade. Force it here.
    procedure = env.ref(
        'remotecontrol_spherag.remotecontrol_spherag_procedure',
        raise_if_not_found=False)
    if procedure:
        procedure.write({'procedure_for_readings': True})
