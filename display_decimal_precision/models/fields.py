# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# v18-safe monkey-patch for Field.get_description to support
# "display precision by application" via ir.config_parameter.

from odoo.fields import Field

_NATIVE_GET_DESCRIPTION = Field.get_description


def _is_ddp_installed(env):
    """Minimal, DB-safe check: is the module installed in this database?"""
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


def _get_dp_scale(env, application):
    """Read scale (display digits) from ir.config_parameter; clamp to [0, 12]."""
    icp = env["ir.config_parameter"].sudo()
    val = icp.get_param(f"customer_purchase_follow_up.dp.{application}")
    try:
        scale = int(val) if val is not None else 2
    except (TypeError, ValueError):
        scale = 2
    return max(0, min(12, scale))


def _new_get_description(self, env, **kwargs):
    """Wrap Field.get_description to inject (16, scale) when appropriate."""
    desc = _NATIVE_GET_DESCRIPTION(self, env, **kwargs)

    # Only touch float fields
    if desc.get("type") != "float":
        return desc

    # 1) Respect explicit digits on the field OR digits already in description
    if desc.get("digits"):
        return desc

    # 2) Only inject when marker is present and addon is installed.
    app = getattr(self, "_related__digits", None)
    if isinstance(app, str) and _is_ddp_installed(env):
        desc["digits"] = (16, _get_dp_scale(env, app))

    return desc


# Apply the monkey-patch
Field.get_description = _new_get_description


def uninstall_hook(_cr, _registry):
    """Restore original Field.get_description on module uninstall."""
    Field.get_description = _NATIVE_GET_DESCRIPTION
