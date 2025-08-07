# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.fields import Field

from odoo.addons.display_decimal_precision.models import DecimalPrecision

native_get_description = Field.get_description


def new_get_description(self, env, **kwargs):
    desc = native_get_description(self, env, **kwargs)
    module_is_installed = False
    display_decimal_precision_ref = env['ir.module.module'].search(
        [('name', '=', 'display_decimal_precision'),
         ('state', '=', 'installed')])
    if display_decimal_precision_ref:
        module_is_installed = True
    if (module_is_installed and hasattr(self, '_related__digits') and
       isinstance(self._related__digits, str)):
        application = self._related__digits
        desc['digits'] = DecimalPrecision.get_display_precision(
            env, application)
    return desc


Field.get_description = new_get_description
