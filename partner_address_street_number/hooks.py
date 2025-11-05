# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

BACKUP_KEY_FMT = "partner_address_street_num.backup_address_format.{country_id}"


def _coerce_env(*args):
    """
    Compatibility helper for Odoo hook signatures.

    Odoo <= 16: hook(cr, registry)
    Odoo >= 17: hook(env)

    Returns a tuple (env, cr).
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
    """
    Insert ' %(street_num)s' right after %(street)s if it is not already present.
    """
    fmt = address_format or ""
    if "%(street_num)s" in fmt:
        return fmt
    return fmt.replace("%(street)s", "%(street)s %(street_num)s")


def _strip_token(address_format: str) -> str:
    """
    Safely remove %(street_num)s (with or without the preceding space) from fmt.
    """
    fmt = address_format or ""
    return fmt.replace(" %(street_num)s", "").replace("%(street_num)s", "")


def post_init_hook(*args):
    """Executed on module installation: injects street_num into country formats."""
    env, _cr = _coerce_env(*args)  # _cr kept for backward compatibility

    # Countries across ALL companies. If none has a country, fallback to ES.
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
                # Store a per-country backup to restore exactly on uninstall
                icp.set_param(BACKUP_KEY_FMT.format(country_id=country.id), old_fmt)
                country.sudo().write({"address_format": new_fmt})
                _logger.info(
                    "partner_address_street_num: injected '%%(street_num)s' into "
                    "%s (%s)",
                    country.name,
                    country.code,
                )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _logger.warning(
                "partner_address_street_num: could not update %s (%s): %s",
                country.name,
                country.code,
                exc,
            )


def uninstall_hook(*args):
    """Executed on module uninstallation: restores or strips the token."""
    env, _cr = _coerce_env(*args)
    icp = env["ir.config_parameter"].sudo()
    countries = env["res.country"].sudo().search([])

    for country in countries:
        try:
            key = BACKUP_KEY_FMT.format(country_id=country.id)
            backup = icp.get_param(key, default=None)
            if backup is not None:
                country.sudo().write({"address_format": backup})
                icp.set_param(key, "")  # clear backup
                _logger.info(
                    "partner_address_street_num: restored backup for %s (%s)",
                    country.name,
                    country.code,
                )
            else:
                old_fmt = country.address_format or ""
                new_fmt = _strip_token(old_fmt)
                if new_fmt != old_fmt:
                    country.sudo().write({"address_format": new_fmt})
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _logger.warning(
                "partner_address_street_num: could not restore %s (%s): %s",
                country.name,
                country.code,
                exc,
            )
