# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# v18-safe monkey-patch for Field.get_description to support
# "display precision by application" using system parameters instead
# of the removed `decimal.precision` model.
#
# Notes:
# - We only touch float fields whose `_related__digits` is a string
#   (application name).
# - We check (and cache) if the `display_decimal_precision` module is
#   installed in the *current database* to avoid cross-DB leakage when
#   switching DBs without restarting the Odoo server.
# - The actual scale is read from ir.config_parameter at:
#     customer_purchase_follow_up.dp.<application>
#   returning (16, scale) like your old API.
#
# You can set values in Settings (via ResConfigSettings fields pointing
# to those keys), or directly with system parameters.

from odoo import tools
from odoo.fields import Field

# Keep a handle to the original so we can restore it on uninstall.
_NATIVE_GET_DESCRIPTION = Field.get_description


@tools.ormcache("env.cr.dbname")
def _is_ddp_installed(env):
    """Fast, per-DB check that the optional module is installed."""
    env.cr.execute(
        """
        SELECT 1
          FROM ir_module_module
         WHERE name = %s AND state = 'installed'
         LIMIT 1
        """,
        ("display_decimal_precision",),
    )
    return bool(env.cr.fetchone())


@tools.ormcache("env.cr.dbname", "application")
def _get_dp_scale(env, application):
    """Fetch scale (display digits) from ir.config_parameter; default=2.

    Key pattern: customer_purchase_follow_up.dp.<application>
    """
    icp = env["ir.config_parameter"].sudo()
    val = icp.get_param(f"customer_purchase_follow_up.dp.{application}")
    try:
        scale = int(val) if val is not None else 2
    except (TypeError, ValueError):
        scale = 2
    # Clamp to a sane range to avoid rendering performance issues
    return max(0, min(12, scale))


def _new_get_description(self, env, **kwargs):
    """Wrap Field.get_description to inject (16, scale) when appropriate."""
    desc = _NATIVE_GET_DESCRIPTION(self, env, **kwargs)

    # Only for float fields and only when `_related__digits` holds the
    # "application" name.
    app = getattr(self, "_related__digits", None)
    if desc.get("type") == "float" and isinstance(app, str) and _is_ddp_installed(env):
        # Don’t overwrite if digits already set explicitly on the field
        # definition (desc["digits"] can be a tuple or a callable).
        if not desc.get("digits"):
            desc["digits"] = (16, _get_dp_scale(env, app))
    return desc


# Apply the monkey-patch
Field.get_description = _new_get_description


# -------------------------
# Uninstall hook (optional)
# -------------------------
def uninstall_hook(_cr, _registry):
    """Restore original Field.get_description on module uninstall."""
    # Use the module-level `Field` reference; avoid re-importing.
    Field.get_description = _NATIVE_GET_DESCRIPTION
