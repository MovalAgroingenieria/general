# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import odoo.modules.module as module_mod


# Assets that base_geoengine incorrectly adds to web.assets_backend.
# These are already included in Odoo's main bundle, so duplicating them
# at the end of the bundle causes typography changes and missing FontAwesome icons.
_ASSETS_TO_REMOVE = {
    'web/static/src/libs/fontawesome/css/font-awesome.css',
    'web/static/src/scss/pre_variables.scss',
    'web/static/lib/bootstrap/scss/_variables.scss',
    ('include', 'web._assets_helpers'),
    ('include', 'web._assets_bootstrap'),
}


def post_load():
    """Remove duplicate assets from base_geoengine's manifest that cause
    typography changes and missing FontAwesome icons in Odoo 16.

    Works by mutating the dict cached by _get_manifest_cached (functools.lru_cache),
    which is the same object read by _fill_asset_paths when building asset bundles.
    This runs at server startup before any request is served.
    """
    manifest = module_mod._get_manifest_cached('base_geoengine')
    backend_assets = manifest.get('assets', {}).get('web.assets_backend', [])
    cleaned = [cmd for cmd in backend_assets if cmd not in _ASSETS_TO_REMOVE]
    manifest.setdefault('assets', {})['web.assets_backend'] = cleaned
