# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.fields import Field

from odoo.addons.display_decimal_precision.models import DecimalPrecision

native_get_description = Field.get_description


def new_get_description(self, env, **kwargs):
    desc = native_get_description(self, env, **kwargs)
    if (hasattr(self, '_related__digits') and
       isinstance(self._related__digits, str)):
        #
        # IMPORTANT (EIS Note):
        #
        # 1. The display_decimal_precision module remains loaded in memory
        # when a database that has it installed is selected. If you switch
        # to another database without restarting the instance, the related
        # code continues to execute.
        #
        # 2. To address this issue, a control has been added to prevent the
        # code from running if display_decimal_precision is not installed.
        # This control must be implemented with great care, since the
        # new_get_description method is executed every time a record with
        # float fields is processed, which can have a significant impact
        # on performance.
        #
        env.cr.execute("""SELECT COUNT(*) FROM ir_module_module
        WHERE name = 'display_decimal_precision' AND state = 'installed'""")
        query_results = env.cr.dictfetchall()
        if query_results and query_results[0].get('count') == 1:
            application = self._related__digits
            desc['digits'] = DecimalPrecision.get_display_precision(
                env, application)
    return desc


Field.get_description = new_get_description
