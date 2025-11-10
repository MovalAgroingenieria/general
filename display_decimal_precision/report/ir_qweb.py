# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.base.models.ir_qweb_fields import FloatConverter

# Keep a reference to the original method to avoid recursion
# and make reverting the patch easier if needed.
_NATIVE_RECORD_TO_HTML = FloatConverter.record_to_html


def _safe_extract_precision(env, field):
    """Return the scale (number of decimals) extracted from
    field.get_description(env). Returns None if not available.
    """
    try:
        desc = field.get_description(env) or {}
        digits = desc.get("digits")
        # In most v18 setups this is already a (precision_total, scale) tuple
        if isinstance(digits, (list, tuple)) and len(digits) == 2:
            return int(digits[1])
        # If digits is missing or not a tuple, do nothing
        return None
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def _patched_record_to_html(self, record, field_name, options=None):
    """Inject 'precision' into options if missing and the field defines one."""
    opts = dict(options or {})
    if "precision" not in opts and "decimal_precision" not in opts:
        field = record._fields.get(field_name)
        if field is not None:
            precision = _safe_extract_precision(record.env, field)
            if precision is not None:
                # Clamp to a safe range to avoid excessive decimals
                precision = max(0, min(12, precision))
                opts["precision"] = precision
    # Call the original method with updated options
    return _NATIVE_RECORD_TO_HTML(self, record, field_name, opts)


# Apply the monkey patch
FloatConverter.record_to_html = _patched_record_to_html
