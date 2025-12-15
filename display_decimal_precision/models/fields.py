# 2023-2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=protected-access

from odoo.fields import Field

native_get_description = Field.get_description


def new_get_description(self, env, attributes=None):
    """Wrap core Field.get_description (Odoo 18 signature).

    Avoid importing our own models package here to prevent circular imports.
    Instead, call the decimal.precision model method through env.
    """
    desc = native_get_description(self, env, attributes=attributes)
    if hasattr(self, "_related__digits") and isinstance(self._related__digits, str):
        application = self._related__digits
        # Force digits in the field description to the configured display precision.
        # get_display_precision is implemented on decimal.precision (in this module).
        desc["digits"] = env["decimal.precision"].get_display_precision(application)
    return desc


Field.get_description = new_get_description
