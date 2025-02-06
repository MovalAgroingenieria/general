# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.fields import Field

from odoo.addons.display_decimal_precision.models import DecimalPrecision as dp

native_get_description = Field.get_description


def new_get_description(self, env, **kwargs):
    desc = native_get_description(self, env, **kwargs)
    if hasattr(self, '_related__digits') and \
            isinstance(self._related__digits, str):
        application = self._related__digits
        desc['digits'] = dp.get_display_precision(env, application)
    return desc


Field.get_description = new_get_description
