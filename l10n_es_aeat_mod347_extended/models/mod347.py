# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería

from odoo import fields, models, api, _


class L10nEsAeatMod347PartnerRecord(models.Model):
    _inherit = 'l10n.es.aeat.mod347.partner_record'

    bdns_number = fields.Char(
        string="BDNS Call Number",
        help="Reference of Call of the subsidy or assistance in National "
             "Grands Database (BDNS).",
    )

    visible_bdns_number = fields.Boolean(
        compute="_compute_visible_bdns_number"
    )

    @api.depends(
        "partner_country_code",
        "partner_state_code",
        "partner_vat",
        "community_vat",
        "operation_key",
        "bdns_number",
    )
    def _compute_check_ok(self):
        for record in self:
            errors = []
            if not record.partner_country_code:
                errors.append(_("Without country code"))
            if not record.partner_state_code:
                errors.append(_("Without state code"))
            if (record.partner_state_code and not
                    record.partner_state_code.isdigit()):
                errors.append(_("State code can only contain digits"))
            if not (record.partner_vat or record.partner_country_code != "ES"):
                errors.append(_("VAT must be defined for Spanish Contacts"))
            if (record.operation_key == "E" and not record.bdns_number) or (
                record.operation_key == "E" and
                record.bdns_number and len(record.bdns_number) != 6
            ):
                # BDSN can have a maximum of 6 digits
                errors.append(
                    _("BDNS Call Number is mandatory for operation key E and "
                      "it must have 6 digits")
                )
            record.check_ok = not bool(errors)
            record.error_text = ", ".join(errors)

    @api.depends("operation_key", "report_id.year")
    def _compute_visible_bdns_number(self):
        for record in self:
            record.visible_bdns_number = (
                record.operation_key == "E" and record.report_id.year >= 2025
            )
