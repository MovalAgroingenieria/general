# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    """Set procedure_for_readings = True on the readings procedure."""
    try:
        procedure = env.ref('remotecontrol_sentilo_aca.'
                            'remotecontrol_sentilo_aca_procedure')
        procedure.write({'procedure_for_readings': True})
    except Exception:
        pass
