# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from markupsafe import Markup, escape
from odoo import api, fields, models
from odoo.tools import format_date, format_datetime

_PREVIEW_TYPES_BY_CATEGORY = {
    "convocation": ("publication",),
    "delegation": (
        "delegation_body",
        "delegation_footer",
        "delegation_combined",
    ),
    "ballots": ("ballot_intro", "ballot_nominative"),
}


def _preview_category_for_document_type(doc_type):
    for cat, keys in _PREVIEW_TYPES_BY_CATEGORY.items():
        if doc_type in keys:
            return cat
    return "convocation"


class AssemblyDocumentPreviewWizard(models.TransientModel):
    _name = "assembly.document.preview.wizard"
    _description = "Preview rendered assembly document HTML"

    assembly_id = fields.Many2one(
        "assembly.assembly",
        required=True,
        readonly=True,
        ondelete="cascade",
        check_company=True,
    )
    document_category = fields.Selection(
        [
            ("convocation", "Convocation"),
            ("delegation", "Delegation"),
            ("ballots", "Ballots"),
        ],
        string="Document group",
        required=True,
        default="convocation",
    )
    document_type_whitelist = fields.Json(
        string="Document type whitelist",
        compute="_compute_document_type_whitelist",
    )
    document_type = fields.Selection(
        [
            ("publication", "Publication / convocation"),
            ("delegation_body", "Delegation document body"),
            ("delegation_footer", "Delegation footer"),
            ("delegation_combined", "Delegation (intro + footer)"),
            ("ballot_intro", "Ballot introduction"),
            ("ballot_nominative", "Nominative ballot introduction"),
        ],
        string="Document",
        required=True,
        default="publication",
    )
    preview_template_kind = fields.Selection(
        [("custom", "Custom template"), ("default", "Default template")],
        string="Template kind",
        readonly=True,
    )
    preview_template_label = fields.Char(string="Template source", readonly=True)
    preview_html = fields.Html(string="Rendered preview", readonly=True, sanitize=False)

    @api.depends("document_category")
    def _compute_document_type_whitelist(self):
        for record in self:
            cat = record.document_category or "convocation"
            keys = _PREVIEW_TYPES_BY_CATEGORY.get(
                cat, _PREVIEW_TYPES_BY_CATEGORY["convocation"]
            )
            record.document_type_whitelist = list(keys)

    @api.model_create_multi
    def create(self, vals_list):
        normalized = []
        for vals in vals_list:
            v = dict(vals)
            doc_type = v.get("document_type", "publication")
            category = v.get("document_category")
            if category is None:
                category = _preview_category_for_document_type(doc_type)
            allowed = _PREVIEW_TYPES_BY_CATEGORY.get(
                category, _PREVIEW_TYPES_BY_CATEGORY["convocation"]
            )
            if doc_type not in allowed:
                doc_type = allowed[0]
            v["document_type"] = doc_type
            v["document_category"] = category
            normalized.append(v)
        records = super().create(normalized)
        for rec in records:
            if rec.assembly_id and rec.document_type:
                rec.write(rec._preview_payload_write_values())
        return records

    def write(self, vals):
        vals = dict(vals)
        if len(self) == 1:
            rec = self
            next_cat = vals.get("document_category", rec.document_category)
            next_dt = vals.get("document_type", rec.document_type)
            if "document_category" in vals and "document_type" not in vals:
                allow = _PREVIEW_TYPES_BY_CATEGORY.get(
                    next_cat, _PREVIEW_TYPES_BY_CATEGORY["convocation"]
                )
                if next_dt not in allow:
                    vals["document_type"] = allow[0]
            elif "document_type" in vals and "document_category" not in vals:
                vals["document_category"] = _preview_category_for_document_type(next_dt)
            elif "document_category" in vals and "document_type" in vals:
                allow = _PREVIEW_TYPES_BY_CATEGORY.get(
                    next_cat, _PREVIEW_TYPES_BY_CATEGORY["convocation"]
                )
                if next_dt not in allow:
                    vals["document_type"] = allow[0]
        res = super().write(vals)
        if any(
            k in vals for k in ("document_type", "assembly_id", "document_category")
        ):
            for record in self:
                record.write(record._preview_payload_write_values())
        return res

    def _format_preview_datetime(self, value):
        if not value:
            return "—"
        out = format_datetime(self.env, value, dt_format="medium")
        return out or "—"

    def _format_preview_date(self, value):
        if not value:
            return "—"
        out = format_date(self.env, value)
        return out or "—"

    def _preview_inner_html_and_kind(self):
        self.ensure_one()
        asm, doc = self.assembly_id, self.document_type
        if not asm or not doc:
            return "", "default"
        renderers = {
            "publication": asm.get_rendered_publication,
            "delegation_body": asm.get_rendered_delegation_document_text,
            "delegation_footer": asm.get_rendered_delegation_footer_text,
            "delegation_combined": asm.get_rendered_delegation,
            "ballot_intro": asm.get_rendered_ballot_intro_text,
            "ballot_nominative_intro": asm.get_rendered_ballot_nominative_intro_text,
        }
        render = renderers.get(doc, asm.get_rendered_ballot_nominative_intro_text)
        return str(render()), "default"

    def _preview_location_line(self, asm):
        """Compose the venue line from location plus city for the preview."""
        loc = (asm.location or "").strip()
        city = ""
        if asm.city_id:
            city = asm.city_id.name
        elif asm.city:
            city = asm.city
        location_line = loc
        if city and city not in location_line:
            location_line = (
                ("%s — %s" % (location_line, city)).strip(" —")
                if location_line
                else city
            )
        return location_line or "—"

    def _preview_call_note(self, asm):
        """Return the scheduling note for the preview header."""
        if asm.date_first_call and asm.date_second_call:
            return self.env._("First and second call scheduled.")
        if asm.date_first_call:
            return self.env._("First call scheduled.")
        if asm.date_second_call:
            return self.env._("Second call scheduled.")
        return ""

    def _wrap_preview_sheet(self, inner_html, label_text, template_kind):
        self.ensure_one()
        asm = self.assembly_id
        if not asm:
            return inner_html or ""
        location_line = self._preview_location_line(asm)
        first = self._format_preview_datetime(asm.date_first_call)
        second = self._format_preview_datetime(asm.date_second_call)
        session = self._format_preview_date(asm.date_start)
        call_note = self._preview_call_note(asm)
        badge_class = (
            "text-bg-primary" if template_kind == "custom" else "text-bg-secondary"
        )
        company = (asm.company_id.name or "").strip() or "—"
        inner_markup = Markup(inner_html) if inner_html else Markup("")
        call_block = (
            Markup('<div class="mt-1 fst-italic">%s</div>') % escape(call_note)
            if call_note
            else Markup("")
        )
        out = (
            Markup(
                '<div class="o_assembly_preview_frame '
                'border rounded-3 bg-100 p-3 mb-2">'
            )
            + Markup(
                '<header class="o_assembly_preview_header d-flex flex-wrap '
                "justify-content-between align-items-start gap-2 mb-3 pb-3 "
                'border-bottom">'
                '<div class="flex-grow-1">'
                '<h4 class="mb-2 fw-bold">%s</h4>'
                '<div class="text-muted small">'
                "<div><strong>%s</strong> %s</div>"
                "<div><strong>%s</strong> %s</div>"
                "<div><strong>%s</strong> %s</div>"
                "<div><strong>%s</strong> %s</div>"
                "<div><strong>%s</strong> %s</div>"
                "</div>"
                "%s"
                "</div>"
                '<span class="badge %s align-self-start">%s</span>'
                "</header>"
            )
            % (
                escape(asm.name or self.env._("Assembly")),
                escape(self.env._("First call:")),
                escape(first),
                escape(self.env._("Second call:")),
                escape(second),
                escape(self.env._("Assembly date:")),
                escape(session),
                escape(self.env._("Location:")),
                escape(location_line),
                escape(self.env._("Company:")),
                escape(company),
                call_block,
                badge_class,
                escape(label_text),
            )
            + Markup(
                '<section class="o_assembly_preview_body border rounded-2 '
                'bg-white p-4 shadow-sm mb-3 mx-auto" '
                'style="max-width: 52rem;">'
            )
            + inner_markup
            + Markup("</section>")
            + Markup(
                '<footer class="o_assembly_preview_footer text-muted small '
                'text-center border-top pt-2">%s</footer>'
                "</div>"
            )
            % escape(
                self.env._(
                    "Preview only — not a signed or filed document. "
                    "Edit the document texts on the assembly (or its type) "
                    "for production output."
                )
            )
        )
        return str(out)

    def _preview_payload_write_values(self):
        self.ensure_one()
        inner, kind = self._preview_inner_html_and_kind()
        label = self.env._("Assembly text")
        return {
            "preview_template_kind": kind,
            "preview_template_label": label,
            "preview_html": self._wrap_preview_sheet(inner, label, kind),
        }

    def action_refresh_preview(self):
        self.ensure_one()
        self.write(self._preview_payload_write_values())
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "base_assembly.action_assembly_document_preview_wizard"
        )
        return {**action, "res_id": self.id}

    @api.onchange("document_category")
    def _onchange_document_category(self):
        if not self.document_category:
            return
        allowed = _PREVIEW_TYPES_BY_CATEGORY[self.document_category]
        if self.document_type not in allowed:
            self.document_type = allowed[0]
        self._onchange_preview_refresh_payload()

    @api.onchange("document_type", "assembly_id")
    def _onchange_document_type_refresh(self):
        if self.document_type:
            self.document_category = _preview_category_for_document_type(
                self.document_type
            )
        self._onchange_preview_refresh_payload()

    def _onchange_preview_refresh_payload(self):
        if self.assembly_id and self.document_type:
            payload = self._preview_payload_write_values()
            self.preview_html = payload["preview_html"]
            self.preview_template_label = payload["preview_template_label"]
            self.preview_template_kind = payload["preview_template_kind"]
