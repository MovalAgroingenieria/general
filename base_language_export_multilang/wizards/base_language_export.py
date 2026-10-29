# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import base64
import io
import zipfile

from odoo import api, fields, models, tools
from odoo.tools.translate import trans_export


class BaseLanguageExport(models.TransientModel):
    _inherit = "base.language.export"

    lang_ids = fields.Many2many(
        "res.lang",
        "base_language_export_lang_rel",
        "wiz_id",
        "lang_id",
        string="Languages",
        domain=[("active", "=", True)],
        help="Select several languages to download a ZIP archive containing "
        "one export per language and an empty translation template. "
        "Leave empty to use Language below.",
    )

    @api.onchange("modules", "export_type")
    def _onchange_modules(self):
        if self.export_type == "module" and len(self.modules) == 1:
            self.lang_ids = self.env["res.lang"].search(
                [("active", "=", True)], limit=None
            )
        else:
            self.lang_ids = False

    def action_select_all_languages(self):
        self.ensure_one()
        self.lang_ids = self.env["res.lang"].search([("active", "=", True)], limit=None)
        return self._reopen_wizard()

    def _reopen_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "views": [(self.env.ref("base.wizard_lang_export").id, "form")],
            "target": "new",
            "context": dict(self.env.context),
        }

    def _export_multiple_languages(self):
        self.ensure_one()
        modules = sorted(self.modules.mapped("name")) or ["all"]
        basename = modules[0] if len(modules) == 1 else "modules"
        with io.BytesIO() as archive_buffer:
            with zipfile.ZipFile(archive_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                for language in self.lang_ids.sorted("code"):
                    with io.BytesIO() as buffer:
                        trans_export(
                            language.code,
                            modules,
                            buffer,
                            self.format,
                            self.env.cr,
                        )
                        filename = f"{tools.get_iso_codes(language.code)}.{self.format}"
                        archive.writestr(filename, buffer.getvalue())
                with io.BytesIO() as buffer:
                    trans_export(False, modules, buffer, "po", self.env.cr)
                    archive.writestr(f"{basename}.pot", buffer.getvalue())
            data = base64.b64encode(archive_buffer.getvalue())
        self.write(
            {
                "state": "get",
                "data": data,
                "name": f"{basename}_translations.zip",
            }
        )
        return self._reopen_wizard()

    def act_getfile(self):
        self.ensure_one()
        if self.export_type == "module":
            if len(self.lang_ids) > 1:
                return self._export_multiple_languages()
            if self.lang_ids:
                self.write({"lang": self.lang_ids.code})
        return super().act_getfile()
