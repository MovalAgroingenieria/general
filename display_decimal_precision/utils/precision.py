# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


def get_display_precision(env, application: str, default_scale: int = 2):
    """Return a (precision, scale) tuple for Float(digits=...).

    In v18 there is no decimal.precision model. We store per-application
    'display digits' in ir.config_parameter under:
        customer_purchase_follow_up.dp.<application>

    :param env: Odoo Env
    :param application: logical name (e.g. 'Product Price', 'Product Unit of Measure')
    :param default_scale: fallback number of decimals if not configured
    :return: (precision, scale) suitable for fields.Float(digits=...)
    """
    icp = env["ir.config_parameter"].sudo()
    key = f"customer_purchase_follow_up.dp.{application}"
    value = icp.get_param(key)
    try:
        scale = int(value) if value is not None else default_scale
    except (TypeError, ValueError):
        scale = default_scale

    # Total precision of 16 keeps parity with your previous return (16, scale).
    # You can raise this if you handle very large whole numbers.
    return 16, max(0, min(12, scale))  # clamp to a sane range
