# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.base.models.ir_qweb_fields import FloatConverter


def record_to_html(self, record, field_name, options):
    if 'precision' not in options and 'decimal_precision' not in options:
        _, precision = \
            record._fields[field_name].get_description(self.env)['digits'] or \
            (None, None)
        options = dict(options, precision=precision)
    return super(FloatConverter, self).record_to_html(
        record, field_name, options)


FloatConverter.record_to_html = record_to_html
