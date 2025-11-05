# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

BACKUP_KEY_FMT = "partner_address_street_type.backup_address_format.{country_id}"
PARAM_KEY = "partner_address_street_type.street_type_shown"


def _coerce_env(*args):
    """
    Odoo <=16: post_init_hook(cr, registry)
    Odoo >=17: post_init_hook(env)
    Devuelve (env, cr)
    """
    if len(args) == 1 and isinstance(args[0], api.Environment):
        env = args[0]
        return env, env.cr
    if len(args) >= 2:
        cr = args[0]
        # registry no se usa, pero podríamos validarlo si quisiéramos
        env = api.Environment(cr, SUPERUSER_ID, {})
        return env, cr
    raise TypeError("Invalid hook signature")


def _inject_token(address_format: str) -> str:
    address_format = address_format or ""
    if "%(street_type_shown)s" in address_format:
        return address_format
    return address_format.replace("%(street)s", "%(street_type_shown)s %(street)s")


def _strip_token(address_format: str) -> str:
    address_format = address_format or ""
    return address_format.replace("%(street_type_shown)s ", "").replace(
        "%(street_type_shown)s", ""
    )


def post_init_hook(*args):
    env, _cr = _coerce_env(*args)
    icp = env["ir.config_parameter"].sudo()

    # Parámetro por defecto del módulo
    icp.set_param(PARAM_KEY, "long")

    # Países de todas las compañías (hook sin usuario real => sudo)
    companies = env["res.company"].sudo().search([])
    countries = companies.mapped("country_id").filtered(lambda c: c)

    if not countries:
        es = env["res.country"].sudo().search([("code", "=", "ES")], limit=1)
        if es:
            countries = es

    for country in countries:
        try:
            old_fmt = country.address_format or ""
            new_fmt = _inject_token(old_fmt)
            if new_fmt != old_fmt:
                # Backup por país para desinstalar limpio
                icp.set_param(BACKUP_KEY_FMT.format(country_id=country.id), old_fmt)
                country.sudo().write({"address_format": new_fmt})
                _logger.info(
                    "partner_address_street_type: injected token into %s (%s)",
                    country.name,
                    country.code,
                )
        except (ValueError, TypeError, AttributeError) as e:
            # Errores específicos que pueden ocurrir durante la manipulación de strings
            _logger.warning(
                "partner_address_street_type: could not update %s (%s): %s",
                country.name,
                country.code,
                e,
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
                icp.set_param(key, "")  # limpiamos backup
                _logger.info(
                    "partner_address_street_type: restored backup for %s (%s)",
                    country.name,
                    country.code,
                )
            else:
                old_fmt = country.address_format or ""
                new_fmt = _strip_token(old_fmt)
                if new_fmt != old_fmt:
                    country.sudo().write({"address_format": new_fmt})
        except (ValueError, TypeError, AttributeError) as e:
            # Errores específicos que pueden ocurrir durante la manipulación de strings
            _logger.warning(
                "partner_address_street_type: could not restore %s (%s): %s",
                country.name,
                country.code,
                e,
            )
