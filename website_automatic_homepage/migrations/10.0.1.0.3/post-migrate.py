# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID

import logging


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    hooks = __import__(
        'odoo.addons.website_automatic_homepage.hooks',
        fromlist=['_ensure_website_name_sync', '_ensure_regantes_channel_setup']
    )
    _ensure_website_name_sync = hooks._ensure_website_name_sync
    _ensure_regantes_channel_setup = hooks._ensure_regantes_channel_setup

    try:
        _ensure_website_name_sync(env)
    except Exception:
        _logger.exception("Could not sync website name.")

    try:
        _ensure_regantes_channel_setup(env)
    except Exception:
        _logger.exception("Could not configure slides channel defaults.")
