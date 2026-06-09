# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Create the default welcome blog post on module update.

    Safe to run multiple times: creation is idempotent and will be skipped
    when an equivalent post already exists.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    hooks = __import__(
        'odoo.addons.website_automatic_homepage.hooks',
        fromlist=['_ensure_website_name_sync', '_ensure_regantes_channel_setup', '_ensure_welcome_blog_post']
    )
    _ensure_website_name_sync = hooks._ensure_website_name_sync
    _ensure_regantes_channel_setup = hooks._ensure_regantes_channel_setup
    _ensure_welcome_blog_post = hooks._ensure_welcome_blog_post

    try:
        _ensure_website_name_sync(env)
    except Exception:
        _logger.exception("Could not sync website name.")

    try:
        _ensure_regantes_channel_setup(env)
    except Exception:
        _logger.exception("Could not configure slides channel defaults.")

    try:
        _ensure_welcome_blog_post(env)
    except Exception:
        _logger.exception("Could not create default welcome blog post.")
