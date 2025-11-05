# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

BACKUP_KEY_FMT = "partner_address_street_num.backup_address_format.{country_id}"


def _coerce_env(*args):
    """
    Odoo <=16: hook(cr, registry)
    Odoo >=17: hook(env)
    Devuelve (env, cr)
    """
    if len(args) == 1 and isinstance(args[0], api.Environment):
        env = args[0]
        return env, env.cr
    if len(args) >= 2:
        cr = args[0]
        env = api.Environment(cr, SUPERUSER_ID, {})
        return env, cr
    raise TypeError("Invalid hook signature")


def _inject_token(address_format: str) -> str:
    """Añade ' %(street_num)s' después de %(street)s si no estaba ya."""
    fmt = address_format or ""
    if "%(street_num)s" in fmt:
        return fmt
    return fmt.replace("%(street)s", "%(street)s %(street_num)s")


def _strip_token(address_format: str) -> str:
    """Elimina %(street_num)s (con o sin espacio previo) de forma segura."""
    fmt = address_format or ""
    return (
        fmt.replace(" %(street_num)s", "")
           .replace("%(street_num)s", "")
    )


def post_init_hook(*args):
    env, _cr = _coerce_env(*args)

    # Países de TODAS las compañías; si ninguna tiene país, intentamos ES.
    companies = env["res.company"].sudo().search([])
    countries = companies.mapped("country_id").filtered(lambda c: c)
    if not countries:
        es = env["res.country"].sudo().search([("code", "=", "ES")], limit=1)
        if es:
            countries = es

    icp = env["ir.config_parameter"].sudo()

    for country in countries:
        try:
            old_fmt = country.address_format or ""
            new_fmt = _inject_token(old_fmt)
            if new_fmt != old_fmt:
                # Guardamos backup por país para restaurar exactamente en uninstall
                icp.set_param(BACKUP_KEY_FMT.format(country_id=country.id), old_fmt)
                country.sudo().write({"address_format": new_fmt})
                _logger.info(
                    "partner_address_street_num: injected '%%(street_num)s' into %s (%s)",
                    country.name, country.code
                )
        except Exception as e:
            _logger.warning(
                "partner_address_street_num: could not update %s (%s): %s",
                country.name, country.code, e
            )


def uninstall_hook(*args):
    env, _cr = _coerce_env(*args)
    icp = env["ir.config_parameter"].sudo()
    countries = env["res.country"].sudo().search([])

    for country in countries:
        try:
            key = BACKUP_KEY_FMT.format(country_id=country.id)
            backup = icp.get_param(key, default=None)
            if backup is not None:
                country.sudo().write({"address_format": backup})
                icp.set_param(key, "")  # limpiar backup
                _logger.info(
                    "partner_address_street_num: restored backup for %s (%s)",
                    country.name, country.code
                )
            else:
                old_fmt = country.address_format or ""
                new_fmt = _strip_token(old_fmt)
                if new_fmt != old_fmt:
                    country.sudo().write({"address_format": new_fmt})
        except Exception as e:
            _logger.warning(
                "partner_address_street_num: could not restore %s (%s): %s",
                country.name, country.code, e
            )
