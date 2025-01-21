# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.config_parameter'].set_param(
        'partner_address_street_type.street_type_shown', 'long')
    company_country_code = False
    company_country_code = env['res.country'].search(
        [('code', '=', env.company.country_id.code)],
        limit=1).code
    if not company_country_code:
        company_country_code = "ES"
    # Add street type to address format of company country
    query = f"""
        UPDATE res_country
        SET address_format = replace(address_format,
        E'%(street)s',E'%(street_type_shown)s %(street)s')
        WHERE code = '{company_country_code}';"""
    try:
        cr.execute(query)
    except Exception:
        pass


def uninstall_hook(cr, registry):
    # Remove street type from address format (all countries)
    query = """
        UPDATE res_country
        SET address_format = replace(
        address_format,
        E'%(street_type_shown)s','');"""
    try:
        cr.execute(query)
    except Exception:
        pass
