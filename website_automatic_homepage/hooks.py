# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from lxml import etree

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


DEFAULT_HOMEPAGE_ARCH = """<t name="Homepage" t-name="website.homepage">
    <t t-call="website.layout">
        <t t-set="pageName" t-value="'homepage'"/>
        <div id="wrap" class="oe_structure oe_empty"/>
    </t>
</t>"""


def _homepage_is_default(view):
    """Return True if the homepage view has not been customized.

    The default homepage shipped by the website module contains an empty
    ``<div id="wrap" class="oe_structure oe_empty"/>``. Any user
    customization replaces that empty div with snippets, so detecting an
    empty wrap is a safe-enough heuristic to avoid overwriting user
    content.
    """
    try:
        root = etree.fromstring(view.arch.encode("utf-8"))
    except Exception:
        return False
    wrap = root.find(".//*[@id='wrap']")
    if wrap is None:
        return False
    # No element children inside wrap -> still the default empty homepage.
    return len(wrap) == 0


def _materialize_company_name(arch, company_name):
    """Replace ``<t t-esc="res_company.name"/>`` with literal text.

    The website editor disables in-place editing for any block that
    contains QWeb directives (``t-esc``, ``t-if``...). Rendering the
    company name to plain text at install time keeps the snippets fully
    editable from the website builder.
    """
    root = etree.fromstring(arch.encode("utf-8"))
    nsmap = {"t": "http://www.w3.org/1999/xhtml"}
    # Match by attribute, no namespaces are actually declared.
    for node in root.xpath("//t[@t-esc='res_company.name']"):
        parent = node.getparent()
        if parent is None:
            continue
        # Preserve surrounding text by appending to parent.text or
        # previous sibling's tail.
        previous = node.getprevious()
        if previous is not None:
            previous.tail = (previous.tail or "") + company_name + (node.tail or "")
        else:
            parent.text = (parent.text or "") + company_name + (node.tail or "")
        parent.remove(node)
    return etree.tostring(root, encoding="unicode")


def post_init_hook(cr, registry):
    """Replace the default empty homepage with the Moval homepage.

    - Only runs on install of this module (not on -u).
    - Skips overwriting if the current homepage has already been
      customized through the website builder.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    homepage = env.ref("website.homepage", raise_if_not_found=False)
    source = env.ref(
        "website_automatic_homepage.homepage_arch_source",
        raise_if_not_found=False,
    )
    if not homepage or not source:
        _logger.warning(
            "Cannot install Moval homepage: "
            "missing website.homepage or homepage_arch_source view."
        )
        return
    if not _homepage_is_default(homepage):
        _logger.info(
            "website.homepage already customized; "
            "skipping Moval homepage installation."
        )
        return
    company = env["res.company"].browse(
        env["res.users"].browse(SUPERUSER_ID).company_id.id
    )
    arch = _materialize_company_name(source.arch, company.name or "")
    homepage.sudo().write({"arch": arch})
    _logger.info("Moval homepage installed in website.homepage view.")

    # Remove auto-created top menu entries from optional dependencies
    # (Blog and Presentations) so the header keeps only our entries.
    for xmlid in (
        "website_blog.menu_news",
        "website_slides.website_menu_slides",
    ):
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu:
            menu.sudo().unlink()


def _homepage_matches_source(homepage, source, company_name):
    """True if the current homepage arch is exactly our installed arch."""
    try:
        installed = _materialize_company_name(source.arch, company_name)
        current = etree.tostring(etree.fromstring(homepage.arch.encode("utf-8")))
        original = etree.tostring(etree.fromstring(installed.encode("utf-8")))
    except Exception:
        return False
    return current == original


def uninstall_hook(cr, registry):
    """Restore the default empty website homepage on uninstall.

    Only resets the homepage if its current arch is exactly the one
    installed by this module, so user customizations made afterwards are
    preserved.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    homepage = env.ref("website.homepage", raise_if_not_found=False)
    source = env.ref(
        "website_automatic_homepage.homepage_arch_source",
        raise_if_not_found=False,
    )
    if not homepage:
        return
    company = env["res.users"].browse(SUPERUSER_ID).company_id
    if source and not _homepage_matches_source(
            homepage, source, company.name or ""):
        _logger.info(
            "website.homepage was modified after install; "
            "leaving it untouched on uninstall."
        )
        return
    homepage.sudo().write({"arch": DEFAULT_HOMEPAGE_ARCH})
