# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
# Ported from OCA/server-tools 14.0/cron_daylight_saving_time_resistant

{
    "name": "Cron daylight saving time resistant",
    "summary": "Run scheduled actions on a stable local wall time across DST changes",
    "description": (
        "When enabled on a scheduled action, adjusts nextcall after DST jumps "
        "so the job keeps the same local clock time (OCA server-tools port)."
    ),
    "version": "10.0.1.0.0",
    "category": "Tools",
    "website": "https://github.com/OCA/server-tools",
    "author": "Akretion, Odoo Community Association (OCA), Moval Agroingeniería",
    "license": "AGPL-3",
    "depends": [
        "base",
    ],
    "data": [
        "views/ir_cron_views.xml",
    ],
    "installable": True,
    "application": False,
}
