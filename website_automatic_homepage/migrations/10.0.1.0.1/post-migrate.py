# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, SUPERUSER_ID

from odoo.addons.website_automatic_homepage.hooks import (
    _materialize_company_name,
)

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Re-materialize ``res_company.name`` in the homepage arch.

    Older versions of this module wrote ``<t t-esc="res_company.name"/>``
    into the website homepage view. The website builder refuses to edit
    sections that contain QWeb directives, so this migration replaces
    those directives with the literal company name to restore editing.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    homepage = env.ref("website.homepage", raise_if_not_found=False)
    if not homepage or "res_company.name" not in (homepage.arch or ""):
        return
    company = env["res.users"].browse(SUPERUSER_ID).company_id
    try:
        new_arch = _materialize_company_name(
            homepage.arch, company.name or ""
        )
    except Exception:
        _logger.exception(
            "Could not re-materialize res_company.name in website.homepage."
        )
        return
    homepage.sudo().write({"arch": new_arch})
    _logger.info(
        "website.homepage arch re-materialized with company name."
    )
