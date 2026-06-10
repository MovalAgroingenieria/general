# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from lxml import etree

from odoo import api, fields, SUPERUSER_ID

_logger = logging.getLogger(__name__)


DEFAULT_HOMEPAGE_ARCH = """<t name="Homepage" t-name="website.homepage">
    <t t-call="website.layout">
        <t t-set="pageName" t-value="'homepage'"/>
        <div id="wrap" class="oe_structure oe_empty"/>
    </t>
</t>"""


WELCOME_POST_TITLE = u"Bienvenidos a nuestra web"
WELCOME_POST_MARKER = u"Bienvenidos a la web de la Comunidad de Regantes."
REGANTES_CHANNEL_NAME = u"Zona Regantes"
LEGAL_FOOTER_KEEP_XMLID = "website_automatic_homepage.layout_footer_copyright_legal_links"
WELCOME_POST_CONTENT = u"""
<section class="s_text_block">
    <div class="container">
        <div class="row">
            <div class="col-md-12 mt16 mb16">
                <h3>Bienvenidos a la web de la Comunidad de Regantes.</h3>
                <p>En este portal web podrás encontrar toda la información referente a nuestra Comunidad.</p>
                <p>Pondremos a disposición de todos los usuarios la información de contacto con nuestra comunidad, noticias sobre nuestras actividades, normas de riego, e incluso una zona privada al que solo podrán tener acceso nuestros comuneros.</p>
                <p><strong>¡Navega y descubre!</strong></p>
            </div>
        </div>
    </div>
</section>
"""


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


def _ensure_welcome_blog_post(env):
    """Ensure a default welcome post exists and is visible in latest posts."""
    Blog = env["blog.blog"].sudo()
    Post = env["blog.post"].sudo()

    blog = env.ref("website_blog.blog_blog_1", raise_if_not_found=False)
    if not blog:
        blog = Blog.search([], order="id", limit=1)
    if not blog:
        blog = Blog.create({"name": u"Noticias"})

    # Set subtitle to "Descúbrenos" and clear About Us sidebar
    if blog.subtitle != u"Descúbrenos":
        blog.write({"subtitle": u"Descúbrenos"})
    # Also update translation cache for subtitle
    env.cr.execute(
        """UPDATE ir_translation
              SET value = %s
            WHERE name = 'blog.blog,subtitle'
              AND res_id = %s""",
        (u"Descúbrenos", blog.id),
    )
    # Disable "About Us" right column widget
    about_us_view = env.ref("website_blog.opt_blog_rc_about_us", raise_if_not_found=False)
    if about_us_view and about_us_view.active:
        about_us_view.sudo().write({"active": False})
        _logger.info("Disabled About Us blog sidebar widget.")

    existing = Post.search([
        '|',
        ('name', '=', WELCOME_POST_TITLE),
        ('content', 'ilike', WELCOME_POST_MARKER),
    ], limit=1)
    if existing:
        vals = {}
        if existing.name == WELCOME_POST_TITLE or WELCOME_POST_MARKER in (existing.content or ""):
            vals["content"] = WELCOME_POST_CONTENT
        if existing.blog_id != blog:
            vals["blog_id"] = blog.id
        if not existing.website_published:
            vals["website_published"] = True
        if not existing.published_date:
            vals["published_date"] = fields.Datetime.now()
        if vals:
            existing.write(vals)
        _logger.info(
            "Welcome post already exists (%s); updated if needed.",
            existing.id,
        )
        return

    post = Post.create({
        "name": WELCOME_POST_TITLE,
        "blog_id": blog.id,
        "content": WELCOME_POST_CONTENT,
        "website_published": True,
        "published_date": fields.Datetime.now(),
    })
    _logger.info("Welcome post created automatically (id=%s).", post.id)


def _ensure_website_name_sync(env):
    """Sync website name with company name."""
    company = env["res.users"].browse(SUPERUSER_ID).company_id
    websites = env["website"].sudo().search([])
    for website in websites:
        if website.company_id == company and website.name != company.name:
            website.sudo().write({"name": company.name})
            _logger.info("Website name updated to '%s'.", company.name)


def _ensure_regantes_channel_setup(env):
    """Rename partner channel and disable featured slide policy."""
    channel = env.ref("website_slides.channel_partial", raise_if_not_found=False)
    if not channel:
        channel = env["slide.channel"].sudo().search([
            ("visibility", "=", "partial"),
        ], order="id", limit=1)
    if not channel:
        channel = env["slide.channel"].sudo().search([
            ("name", "ilike", "Partner"),
        ], limit=1)
    if not channel:
        _logger.info("Slides partner channel not found; skipping setup.")
        return

    vals = {}
    if channel.name != REGANTES_CHANNEL_NAME:
        vals["name"] = REGANTES_CHANNEL_NAME
    if channel.promote_strategy != "none":
        vals["promote_strategy"] = "none"
    if channel.custom_slide_id:
        vals["custom_slide_id"] = False

    if vals:
        channel.sudo().write(vals)
        _logger.info("Slides channel configured as '%s' with no featured slide.", REGANTES_CHANNEL_NAME)

    # Force update all cached translations for the channel name so the
    # website always shows "Zona Regantes" regardless of active language.
    env.cr.execute(
        """UPDATE ir_translation
              SET value = %s, src = %s
            WHERE name = 'slide.channel,name'
              AND res_id = %s""",
        (REGANTES_CHANNEL_NAME, REGANTES_CHANNEL_NAME, channel.id),
    )
    _logger.info(
        "Updated %d ir_translation rows for channel id=%s.",
        env.cr.rowcount, channel.id,
    )


def _disable_duplicated_legal_footer_blocks(env):
    """Keep only our legal footer links block active.

    Some databases may keep residual inherited footer views (from old
    modules/customizations) that inject legal links a second time.
    This safeguard deactivates those duplicates during install.
    """
    View = env["ir.ui.view"].sudo()

    keep_view = env.ref(LEGAL_FOOTER_KEEP_XMLID, raise_if_not_found=False)
    keep_id = keep_view.id if keep_view else False

    parent_ids = []
    for parent_xmlid in ("website.layout_footer_copyright", "website.footer_default"):
        parent = env.ref(parent_xmlid, raise_if_not_found=False)
        if parent:
            parent_ids.append(parent.id)
    if not parent_ids:
        return

    candidates = View.search([
        ("active", "=", True),
        ("inherit_id", "in", parent_ids),
    ])

    deactivated = 0
    for view in candidates:
        if keep_id and view.id == keep_id:
            continue

        haystack = u" ".join([
            view.key or u"",
            view.name or u"",
            view.arch_db or u"",
        ]).lower()

        is_legal_block = any(token in haystack for token in (
            u"aviso legal",
            u"legal links",
            u"legal notice",
            u"política de privacidad",
            u"politica de privacidad",
            u"privacy policy",
            u"política de cookies",
            u"politica de cookies",
            u"/page/aviso-legal",
            u"/page/politica-privacidad",
            u"/page/politica-cookies",
        ))
        if not is_legal_block:
            continue

        view.write({"active": False})
        deactivated += 1

    if deactivated:
        _logger.info(
            "Deactivated %d duplicated legal footer view(s); keeping %s.",
            deactivated,
            LEGAL_FOOTER_KEEP_XMLID,
        )


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
    else:
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

    _disable_duplicated_legal_footer_blocks(env)
    _ensure_website_name_sync(env)
    _ensure_regantes_channel_setup(env)
    _ensure_welcome_blog_post(env)


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
