# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import contextlib
import cStringIO
import zipfile

from odoo import api, fields, models, tools


class BaseLanguageExport(models.TransientModel):
    _inherit = 'base.language.export'

    lang_ids = fields.Many2many(
        'res.lang',
        'base_language_export_lang_rel',
        'wiz_id',
        'lang_id',
        string='Languages',
        domain=[('translatable', '=', True)],
           help='Select several languages to download a ZIP archive containing '
               'one export per language. Leave empty to use Language below.',
    )

    @api.onchange('modules')
    def _onchange_modules(self):
        if len(self.modules) == 1:
            self.lang_ids = self.env['res.lang'].search(
                [('translatable', '=', True)]
            )
        else:
            self.lang_ids = False

    @api.multi
    def action_select_all_languages(self):
        self.ensure_one()
        self.lang_ids = self.env['res.lang'].search(
            [('translatable', '=', True)]
        )
        return self._reopen_wizard()

    @api.multi
    def _reopen_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'view_type': 'form',
            'views': [(self.env.ref('base.wizard_lang_export').id, 'form')],
            'target': 'new',
            'context': dict(self.env.context),
        }

    @api.multi
    def _export_multiple_languages(self):
        self.ensure_one()
        modules = sorted(self.modules.mapped('name')) or ['all']
        with contextlib.closing(cStringIO.StringIO()) as archive_buffer:
            with zipfile.ZipFile(archive_buffer, 'w',
                                 zipfile.ZIP_DEFLATED) as archive:
                for language in self.lang_ids.sorted('code'):
                    with contextlib.closing(cStringIO.StringIO()) as buffer:
                        tools.trans_export(language.code, modules, buffer,
                                           self.format, self.env.cr)
                        filename = '%s.%s' % (
                            tools.get_iso_codes(language.code), self.format)
                        archive.writestr(filename, buffer.getvalue())
                with contextlib.closing(cStringIO.StringIO()) as buffer:
                    tools.trans_export(False, modules, buffer, 'po',
                                       self.env.cr)
                    template_name = '%s.pot' % (
                        modules[0] if len(modules) == 1 else 'modules')
                    archive.writestr(template_name, buffer.getvalue())
            data = base64.b64encode(archive_buffer.getvalue())
        self.write({
            'state': 'get',
            'data': data,
            'name': '%s_translations.zip' % (
                modules[0] if len(modules) == 1 else 'modules'),
        })
        return self._reopen_wizard()

    @api.multi
    def act_getfile(self):
        self.ensure_one()
        if len(self.lang_ids) > 1:
            action = self._export_multiple_languages()
        else:
            if self.lang_ids:
                self.lang = self.lang_ids.code
            action = super(BaseLanguageExport, self).act_getfile()
        return action
