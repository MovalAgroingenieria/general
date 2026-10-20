# -*- coding: utf-8 -*-
# Copyright 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import csv
import tarfile
import zipfile
from cStringIO import StringIO

from odoo.tests.common import TransactionCase


class TestBaseLanguageExport(TransactionCase):

    def setUp(self):
        super(TestBaseLanguageExport, self).setUp()
        self.module = self.env['ir.module.module'].search([
            ('name', '=', 'base_language_export_multilang'),
        ])
        self.languages = self.env['res.lang'].with_context(
            active_test=False).search([('code', 'in', ['es_ES', 'ca_ES'])])
        self.assertEqual(len(self.languages), 2)
        self.languages.write({'active': True, 'translatable': True})
        self.wizard = self.env['base.language.export'].create({
            'modules': [(6, 0, self.module.ids)],
            'format': 'po',
        })
        field = self.env.ref(
            'base_language_export_multilang.'
            'field_base_language_export_lang_ids')
        for language in self.languages:
            self.env['ir.translation'].create({
                'name': 'ir.model.fields,field_description',
                'type': 'model',
                'lang': language.code,
                'res_id': field.id,
                'src': 'Languages',
                'value': 'Idiomas' if language.code == 'es_ES' else 'Idiomes',
                'module': self.module.name,
            })

    def test_select_all_keeps_wizard_open(self):
        expected = self.env['res.lang'].search([
            ('translatable', '=', True),
        ])
        action = self.wizard.action_select_all_languages()
        self.assertEqual(set(self.wizard.lang_ids.ids), set(expected.ids))
        self.assertIsInstance(action, dict)
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], self.wizard._name)
        self.assertEqual(action['res_id'], self.wizard.id)
        self.assertEqual(action['target'], 'new')
        self.assertEqual(self.wizard.state, 'choose')

    def test_select_all_excludes_unloaded_languages(self):
        self.languages[0].translatable = False
        self.languages[1].active = False
        self.wizard.action_select_all_languages()
        self.assertFalse(self.wizard.lang_ids & self.languages)

    def test_module_onchange(self):
        self.wizard._onchange_modules()
        self.assertTrue(self.languages <= self.wizard.lang_ids)
        self.wizard.modules = False
        self.wizard._onchange_modules()
        self.assertFalse(self.wizard.lang_ids)

    def test_export_multiple_po_languages(self):
        self.wizard.lang_ids = self.languages
        action = self.wizard.act_getfile()
        self.assertEqual(action['res_id'], self.wizard.id)
        self.assertEqual(self.wizard.state, 'get')
        self.assertTrue(self.wizard.name.endswith('.zip'))
        archive = zipfile.ZipFile(StringIO(
            base64.b64decode(self.wizard.data)))
        try:
            expected = ['es.po', 'ca_ES.po', '%s.pot' % self.module.name]
            self.assertEqual(set(archive.namelist()), set(expected))
            self.assertIn('msgstr "Idiomas"', archive.read('es.po'))
            self.assertIn('msgstr "Idiomes"', archive.read('ca_ES.po'))
            template = archive.read('%s.pot' % self.module.name)
            self.assertIn('msgid "Languages"\nmsgstr ""', template)
            self.assertNotIn('msgstr "Idiomas"', template)
            self.assertNotIn('msgstr "Idiomes"', template)
        finally:
            archive.close()

    def test_export_multiple_csv_languages(self):
        self.wizard.write({
            'lang_ids': [(6, 0, self.languages.ids)],
            'format': 'csv',
        })
        self.wizard.act_getfile()
        archive = zipfile.ZipFile(StringIO(
            base64.b64decode(self.wizard.data)))
        try:
            for filename, value in [('es.csv', 'Idiomas'),
                                    ('ca_ES.csv', 'Idiomes')]:
                rows = list(csv.DictReader(StringIO(archive.read(filename))))
                self.assertTrue(any(row['src'] == 'Languages' and
                                    row['value'] == value for row in rows))
            self.assertIn('msgid "Languages"\nmsgstr ""',
                          archive.read('%s.pot' % self.module.name))
        finally:
            archive.close()

    def test_export_multiple_tgz_languages(self):
        self.wizard.write({
            'lang_ids': [(6, 0, self.languages.ids)],
            'format': 'tgz',
        })
        self.wizard.act_getfile()
        archive = zipfile.ZipFile(StringIO(
            base64.b64decode(self.wizard.data)))
        try:
            for language in self.languages:
                filename = '%s.tgz' % (
                    'es' if language.code == 'es_ES' else language.code)
                tar = tarfile.open(fileobj=StringIO(archive.read(filename)),
                                   mode='r:gz')
                try:
                    member = next(item for item in tar.getmembers()
                                  if item.name.endswith('.po'))
                    value = ('Idiomas' if language.code == 'es_ES'
                             else 'Idiomes')
                    self.assertIn('msgstr "%s"' % value,
                                  tar.extractfile(member).read())
                finally:
                    tar.close()
            self.assertIn('msgid "Languages"\nmsgstr ""',
                          archive.read('%s.pot' % self.module.name))
        finally:
            archive.close()

    def test_export_single_language(self):
        self.wizard.lang_ids = self.languages.filtered(
            lambda language: language.code == 'es_ES')
        self.wizard.act_getfile()
        self.assertEqual(self.wizard.name, 'es.po')
        self.assertIn('msgstr "Idiomas"',
                      base64.b64decode(self.wizard.data))

    def test_export_template(self):
        self.wizard.act_getfile()
        self.assertEqual(self.wizard.name, '%s.pot' % self.module.name)
        self.assertIn('msgid "Languages"\nmsgstr ""',
                      base64.b64decode(self.wizard.data))