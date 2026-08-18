# -*- coding: utf-8 -*-
# 2026 Moval Agroingenieria
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import os
import subprocess

from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

import logging
_logger = logging.getLogger(__name__)


def _normalize_filepath(path):
    path = path or ''
    path = path.strip()
    if not os.path.isabs(path):
        return False
    path = os.path.normpath(path)
    return path if os.path.exists(path) else False


def _is_signing_disabled(value):
    return (value or '').strip() == '-'


class Report(models.Model):
    _inherit = 'report'

    def _certificate_get(self, report, docids):
        certificate = super(Report, self)._certificate_get(report, docids)
        if not certificate:
            return False
        if (_is_signing_disabled(certificate.path) or
                _is_signing_disabled(certificate.password_file)):
            _logger.debug(
                "Certificate '%s' skipped because path/password is '-'",
                certificate.name)
            return False
        if certificate.domain:
            domain = [('id', 'in', tuple(docids))]
            domain = domain + safe_eval(certificate.domain)
            docs = self.env[certificate.model_id.model].search(domain)
            if not docs:
                _logger.debug(
                    "Certificate '%s' domain not satisfied",
                    certificate.name)
                return False
        return certificate

    def pdf_sign(self, pdf, certificate):
        pdfsigned = pdf + '.signed.pdf'
        p12 = _normalize_filepath(certificate.path)
        passwd = _normalize_filepath(certificate.password_file)
        if not (p12 and passwd):
            raise UserError(
                _('Signing report (PDF): '
                  'Certificate or password file not found'))
        signer_opts = '"%s" "%s" "%s" "%s"' % (p12, pdf, pdfsigned, passwd)
        signer = self._signer_bin(signer_opts)
        process = subprocess.Popen(
            signer, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = process.communicate()
        if process.returncode:
            raise UserError(
                _('Signing report (PDF): jPdfSign failed (error code: %s). '
                  'Message: %s. Output: %s') %
                (process.returncode, err, out))
        return pdfsigned
