# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import tempfile
from contextlib import closing
import os
import glob
import subprocess

from odoo import models, exceptions, _


def _normalize_filepath(path):
    path = path or ''
    path = path.strip()
    if not os.path.isabs(path):
        return False
    path = os.path.normpath(path)
    return path if os.path.exists(path) else False


class Report(models.Model):
    _inherit = 'ir.actions.report'

    PAGE_OF_SIGNATURE = 1
    LLX_FOR_SIGNATURE = 30
    LLY_FOR_SIGNATURE = 70
    URX_FOR_SIGNATURE = 225
    URY_FOR_SIGNATURE = 193
    MAX_SIGNATURES = 2
    COLUMN_SPACING = 110
    FIT_IMAGE = True

    def get_pdf(self, docids, report_name, html=None, data=None):
        resp = False
        call_parent_method = True
        report = self._get_report_from_name(report_name)
        if report and report.model == 'eom.electronicfile.communication':
            sign_certicate_ok = self._check_sign_certificate()
            if sign_certicate_ok:
                call_parent_method = False
        if call_parent_method:
            resp = report._render_qweb_pdf(
                report_name, docids, data=data)
        else:
            content = report._render_qweb_pdf(
                self, report_name, docids, data=data)
            p12_file, passwd_file = self._get_sign_certificate()
            signature_parameters = self._get_signature_parameters()

            pdf_fd, pdf = tempfile.mkstemp(suffix='.pdf', prefix='report.tmp.')
            with closing(os.fdopen(pdf_fd, 'w')) as pf:
                pf.write(content)
            signed = self.pdf_sign_with_visible_signature(
                pdf, p12_file, passwd_file, signature_parameters)
            if os.path.exists(signed):
                with open(signed, 'rb') as pf:
                    content = pf.read()
            for fname in (pdf, signed):
                try:
                    os.unlink(fname)
                except Exception:
                    pass
                resp = content
        return resp

    def pdf_sign_with_visible_signature(
            self, pdf, p12_file, passwd_file, signature_parameters):
        with open(passwd_file, 'rb') as pf:
            passwd = pf.readline().rstrip()
        # Vars
        background_img = self._get_background_img(os.path.dirname(p12_file))
        current_dir = os.path.dirname(__file__)
        jar_path = current_dir + '/../static/jar'
        jar_file = jar_path + '/JSignPdf.jar'
        output_dir = os.path.dirname(pdf)
        # Parameters
        page_of_signature = signature_parameters['page_of_signature']
        column_spacing = signature_parameters['column_spacing']
        llx_for_signature = signature_parameters['llx_for_signature']
        urx_for_signature = signature_parameters['urx_for_signature']
        width_for_signature = (urx_for_signature - llx_for_signature) + \
            column_spacing
        number_of_signature = 1
        if number_of_signature > 1:
            llx_for_signature = (number_of_signature - 1) * width_for_signature
            urx_for_signature = llx_for_signature + urx_for_signature
        lly_for_signature = signature_parameters['lly_for_signature']
        ury_for_signature = signature_parameters['ury_for_signature']
        fit_image = signature_parameters['fit_image']
        # Path of signed pdf
        pdf_name = os.path.splitext(pdf)[0]
        pdf_signed = pdf_name + '_signed.pdf'
        # Call the jar file
        exec_line = 'java -Djsignpdf.home=' + jar_path + \
            ' -jar ' + jar_file + \
            ' -ksf ' + p12_file + \
            ' -ksp ' + passwd + \
            ' ' + pdf + \
            ' -d ' + output_dir + \
            ' -q' + \
            ' -pg ' + str(page_of_signature) + \
            ' -V' + \
            ' -llx ' + str(llx_for_signature) + \
            ' -lly ' + str(lly_for_signature) + \
            ' -urx ' + str(urx_for_signature) + \
            ' -ury ' + str(ury_for_signature)
        if background_img:
            bg_scale = 0
            if fit_image:
                bg_scale = -1
            exec_line = exec_line + \
                ' --bg-path ' + background_img + \
                ' --bg-scale ' + str(bg_scale)
        process = subprocess.Popen(exec_line, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=True)
        out, err = process.communicate()
        if process.returncode:
            raise exceptions.UserError(
                _('Signing report (PDF): jPdfSign failed (error code: %s). '
                  'Message: %s. Output: %s') %
                (process.returncode, err, out))
        for fname in (pdf):
            try:
                os.unlink(fname)
            except Exception:
                pass
        return pdf_signed

    def _get_signature_parameters(self):
        resp = {
            'page_of_signature': self.PAGE_OF_SIGNATURE,
            'llx_for_signature': self.LLX_FOR_SIGNATURE,
            'lly_for_signature': self.LLY_FOR_SIGNATURE,
            'urx_for_signature': self.URX_FOR_SIGNATURE,
            'ury_for_signature': self.URY_FOR_SIGNATURE,
            'max_signatures': self.MAX_SIGNATURES,
            'column_spacing': self.COLUMN_SPACING,
            'fit_image': self.FIT_IMAGE,
            }
        return resp

    def _get_background_img(self, path):
        resp = ''
        for file_name in (glob.glob(path + '/*.png') or []):
            resp = file_name
            break
        if not resp:
            for file_name in (glob.glob(path + '/*.jpg') or []):
                resp = file_name
                break
        if not resp:
            for file_name in (glob.glob(path + '/*.jpeg') or []):
                resp = file_name
                break
        return resp

    def _check_sign_certificate(self):
        sign_certicate_ok = False
        sign_certificate_path = self.env['ir.default'].get(
            'res.config.settings', 'eom_eoffice.sign_certificate_path')
        sign_certificate_password_path = self.env['ir.default'].get(
            'res.config.settings',
            'eom_eoffice.sign_certificate_password_path')
        if sign_certificate_path and sign_certificate_password_path:
            p12_file_ok = os.access(
                _normalize_filepath(sign_certificate_path), os.R_OK)
            passwd_file_ok = os.access(
                _normalize_filepath(sign_certificate_password_path), os.R_OK)
            if p12_file_ok and passwd_file_ok:
                sign_certicate_ok = True
        return sign_certicate_ok

    def _get_sign_certificate(self):
        p12_file = passwd_file = False
        sign_certificate_path = self.env['ir.default'].get(
            'res.config.settings', 'eom_eoffice.sign_certificate_path')
        sign_certificate_password_path = self.env['ir.default'].get(
            'res.config.settings',
            'eom_eoffice.sign_certificate_password_path')
        if sign_certificate_path and sign_certificate_password_path:
            p12_file = _normalize_filepath(sign_certificate_path)
            passwd_file = _normalize_filepath(sign_certificate_password_path)
        return p12_file, passwd_file
