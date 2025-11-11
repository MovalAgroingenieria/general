# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import datetime as dt

from jinja2 import Template, TemplateError
from odoo import api, exceptions, fields, models


class ResFile(models.Model):
    _name = "res.file"
    _description = "File management"
    _inherit = ["mail.thread", "simple.model", "mail.activity.mixin"]

    # SimpleModel tuning
    _size_name = 50
    _size_description = 100
    _set_num_code = False

    SIZE_ANNUALSEQ_CODE = 4

    # -------------------------
    # Defaults
    # -------------------------

    def _default_file_code(self):
        """Generate next code as <PREFIX>-<YYYY>/<NNNN> per company."""
        current_year = dt.date.today().year
        if not self.env.user.company_id.file_prefix:
            raise exceptions.UserError(
                self.env._(
                    "The file prefix parameter is not set. Go to configuration "
                    "and set a value for the parameter."
                )
            )
        file_prefix = self.env.user.company_id.file_prefix.strip()
        full_prefix = f"{file_prefix}-{current_year:04d}/"
        resp = f"{full_prefix}{1:0{self.SIZE_ANNUALSEQ_CODE}d}"

        last = self.search([("name", "like", full_prefix)], limit=1, order="name desc")
        if last and (last.name or "").startswith(full_prefix):
            numeric_suffix = (last.name or "")[len(full_prefix) :]
            try:
                proposed = int(numeric_suffix)
            except ValueError:
                proposed = 0
            if proposed > 0:
                resp = f"{full_prefix}{(proposed + 1):0{self.SIZE_ANNUALSEQ_CODE}d}"
        return resp

    def _default_category_id(self):
        """Default category: Internal Files (if present)."""
        cat = self.env.ref(
            "crm_filemgmt.resfilecategory_internal_file", raise_if_not_found=False
        )
        return cat.id if cat else False

    # -------------------------
    # Fields
    # -------------------------

    alphanum_code = fields.Char(
        string="Code",
        default=lambda self: self._default_file_code(),  # pylint: disable=protected-access
        required=True,
        index=True,
    )

    date_file = fields.Date(
        string="Discharge date",
        default=fields.Date.context_today,
        required=True,
        index=True,
    )

    subject = fields.Char(required=True, index=True)

    tag_ids = fields.Many2many(
        string="File Tags",
        comodel_name="res.filetag",
        relation="res_file_filetag_rel",
        column1="file_id",
        column2="filetag_id",
    )

    image = fields.Image(string="Photo / Image")

    stage_id = fields.Many2one(
        string="Stage",
        comodel_name="res.file.stage",
        required=True,
        # usa una lambda "pública" para evitar W0212
        default=lambda self: self.env["res.file.stage"]
        .search([], order="sequence, name", limit=1)
        .id,
        group_expand="_read_group_stage_ids",
        tracking=True,
    )

    is_closing_stage = fields.Boolean(compute="_compute_is_closing_stage", store=True)

    is_blocked = fields.Boolean(string="Blocked", default=False, tracking=True)

    notes = fields.Html()

    category_id = fields.Many2one(
        string="Category",
        comodel_name="res.file.category",
        index=True,
        required=True,
        ondelete="restrict",
        default=lambda self: self._default_category_id(),  # pylint: disable=protected-access
    )

    partnerlink_ids = fields.One2many(
        string="Partners", comodel_name="res.file.partnerlink", inverse_name="file_id"
    )

    partner_id = fields.Many2one(
        string="Partner",
        comodel_name="res.partner",
        index=True,
        ondelete="restrict",
        compute="_compute_partner_id",
        store=True,
        tracking=True,
    )

    filelink_ids = fields.One2many(
        string="Files", comodel_name="res.file.filelink", inverse_name="file_id"
    )

    color = fields.Integer(
        string="Color Index",
        default=0,
        help="0:grey, 1:green, 2:yellow, 3:orange, 4:red, 5:purple, 6:blue, "
        "7:cyan, 8:light-green, 9:magenta",
    )

    closing_date = fields.Date(
        string="Closing date", compute="_compute_closing_date", store=True
    )

    container_id = fields.Many2one(
        string="Container", comodel_name="res.file.container"
    )

    file_attachment_ids = fields.One2many(
        string="File attachments",
        comodel_name="ir.attachment",
        compute="_compute_attachments_ids",
    )

    has_filelinks = fields.Boolean(
        string="Has filelinks", compute="_compute_has_filelinks", default=False
    )

    has_attachments = fields.Boolean(
        string="Has attachments", compute="_compute_has_attachments", default=False
    )

    technician_id = fields.Many2one(
        string="Technician", comodel_name="res.partner", index=True
    )

    with_technician = fields.Boolean(
        string="With technician", compute="_compute_with_technician", store=True
    )

    file_top_comment_template_id = fields.Many2one(
        "base.comment.template", string="Top Comment Template"
    )
    file_bottom_comment_template_id = fields.Many2one(
        "base.comment.template", string="Bottom Comment Template"
    )

    file_top_comment = fields.Html(string="Top comment", translate=True)
    file_bottom_comment = fields.Html(string="Bottom comment", translate=True)

    active = fields.Boolean(default=True)

    file_report_id = fields.Many2one(string="Report", comodel_name="res.file.report")

    template_start = fields.Html(string="Template start")
    template_end = fields.Html(string="Template end")

    template_start_rendered = fields.Html(
        string="Template start rendered", compute="_compute_template_start_rendered"
    )
    template_end_rendered = fields.Html(
        string="Template end rendered", compute="_compute_template_end_rendered"
    )

    _sql_constraints = [
        ("unique_name", "UNIQUE (name)", "Existing file code."),
    ]

    # -------------------------
    # Display name (replace name_get)
    # -------------------------
    def _compute_display_name(self):
        for rec in self:
            subj = rec.subject or self.env._("[no subject]")
            base = rec.name or rec.alphanum_code or ""
            rec.display_name = f"{base} [{subj}]"

    # -------------------------
    # Actions
    # -------------------------
    def action_get_start_template(self):
        """Copy the report's start template HTML into the record field."""
        self.ensure_one()
        if not (self.file_report_id and self.file_report_id.report_template_start):
            raise exceptions.UserError(
                self.env._("No report or start template has been selected.")
            )
        self.template_start = self.file_report_id.report_template_start

    def action_get_end_template(self):
        """Copy the report's end template HTML into the record field."""
        self.ensure_one()
        if not (self.file_report_id and self.file_report_id.report_template_end):
            raise exceptions.UserError(
                self.env._("No report or end template has been selected.")
            )
        self.template_end = self.file_report_id.report_template_end

    def action_block_file(self):
        self.ensure_one()
        self.is_blocked = True

    def action_unblock_file(self):
        self.ensure_one()
        self.is_blocked = False

    # -------------------------
    # Computes
    # -------------------------

    def _compute_attachments_ids(self):
        for rec in self:
            rec.file_attachment_ids = rec.env["ir.attachment"].search(
                [("res_model", "=", self._name), ("res_id", "=", rec.id)]
            )

    @api.depends("partnerlink_ids")
    def _compute_partner_id(self):
        for rec in self:
            rec.partner_id = False
            for partner_link in rec.partnerlink_ids:
                if partner_link.is_main:
                    rec.partner_id = partner_link.partner_id
                    break

    @api.depends("stage_id")
    def _compute_is_closing_stage(self):
        for rec in self:
            rec.is_closing_stage = bool(rec.stage_id and rec.stage_id.is_closing_stage)

    @api.depends("stage_id", "is_closing_stage")
    def _compute_closing_date(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.closing_date = today if rec.is_closing_stage else False

    @api.depends("filelink_ids")
    def _compute_has_filelinks(self):
        for rec in self:
            rec.has_filelinks = bool(rec.filelink_ids)

    @api.depends("file_attachment_ids")
    def _compute_has_attachments(self):
        for rec in self:
            rec.has_attachments = bool(rec.file_attachment_ids)

    @api.depends("technician_id")
    def _compute_with_technician(self):
        for rec in self:
            rec.with_technician = bool(rec.technician_id)

    # -------------------------
    # Create / Validations
    # -------------------------

    @api.model_create_multi
    def create(self, vals_list):
        # Validate alphanum_code format when provided explicitly
        first = vals_list[0] if vals_list else {}
        if first.get("alphanum_code"):
            self._check_filecode_format(first["alphanum_code"])
        return super().create(vals_list)

    def _check_filecode_format(self, filecode: str):
        """Ensure <PREFIX>-<YYYY>/<NNNN> shape and sane parts."""

        if filecode.startswith("/") or filecode.endswith("/"):
            raise exceptions.UserError(
                self.env._("The file name cannot start or end with a slash (/).")
            )
        if filecode.count("/") != 1:
            raise exceptions.UserError(
                self.env._("There is more than one slash in the file name.")
            )

        try:
            int(filecode.split("/")[1])
        except ValueError as exc:
            raise exceptions.UserError(
                self.env._("The file number must be an integer.")
            ) from exc

    # -------------------------
    # Stages (kanban)
    # -------------------------

    @api.model
    def _default_stage_id(self):
        """Kept for API compatibility (not used in field default to avoid W0212)."""
        return self.env["res.file.stage"].search([], order="sequence, name", limit=1)

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        # consume domain to avoid unused-argument warning
        _ = domain
        # evita _search protegido
        return stages.search([], limit=100, order=order)

    # -------------------------
    # Constraints (links)
    # -------------------------

    @api.constrains("partnerlink_ids")
    def _check_partnerlink_ids(self):
        for rec in self:
            if not rec:
                continue
            if rec.partnerlink_ids:
                mains = rec.partnerlink_ids.filtered(lambda x: x.is_main)
                if len(mains) == 0:
                    raise exceptions.UserError(
                        self.env._("It is mandatory to check the primary partner.")
                    )
                if len(mains) > 1:
                    raise exceptions.UserError(
                        self.env._("Only one primary partner is allowed.")
                    )
            # No duplicated partners
            partner_ids = [pl.partner_id.id for pl in rec.partnerlink_ids]
            if len(set(partner_ids)) != len(partner_ids):
                raise exceptions.UserError(self.env._("There are repeated partners."))

    @api.constrains("filelink_ids")
    def _check_filelink_ids(self):
        for rec in self:
            if not rec:
                continue
            if rec.filelink_ids:
                # Self reference
                self_ref = self.env["res.file.filelink"].search(
                    [("file_id", "=", rec.id), ("related_file_id", "=", rec.id)],
                    limit=1,
                )
                if self_ref:
                    raise exceptions.UserError(
                        self.env._("The file cannot be self-referenced.")
                    )
            # No duplicates
            rel_ids = [fl.related_file_id.id for fl in rec.filelink_ids]
            if len(set(rel_ids)) != len(rel_ids):
                raise exceptions.UserError(self.env._("There are repeated files."))

    # -------------------------
    # Onchanges
    # -------------------------

    @api.onchange("file_top_comment_template_id")
    def _set_file_top_comment(self):
        if self.file_top_comment_template_id:
            self.file_top_comment = self.file_top_comment_template_id.get_value(
                self.partner_id.id
            )

    @api.onchange("file_bottom_comment_template_id")
    def _set_file_bottom_comment(self):
        if self.file_bottom_comment_template_id:
            self.file_bottom_comment = self.file_bottom_comment_template_id.get_value(
                self.partner_id.id
            )

    @api.onchange("stage_id")
    def _onchange_stage_id(self):
        if self.stage_id.is_closing_stage and (
            self._origin and not self._origin.stage_id.is_closing_stage
        ):
            raise exceptions.UserError(
                self.env._(
                    "You cannot move a file from a non-closing "
                    "stage to a closing stage."
                )
            )

    @api.onchange("file_report_id", "file_report_id.report_template_start")
    def _compute_template_start(self):
        for rec in self:
            if rec.file_report_id and rec.file_report_id.report_template_start:
                rec.template_start = rec.file_report_id.report_template_start

    @api.depends("template_start")
    def _compute_template_start_rendered(self):
        for rec in self:
            rendered = ""
            if rec.template_start:
                try:
                    rendered = Template(rec.template_start).render(record=rec)
                except TemplateError as template_error:
                    rendered = (
                        '<p style="text-align:center;color:red;"><b>'
                        '<font style="font-size: 14px;">'
                        + self.env._("ERROR IN START TEMPLATE")
                        + "</font></b></p><p><br>"
                        + str(template_error)
                        + "</p>"
                    )
            rec.template_start_rendered = rendered

    @api.onchange("file_report_id", "file_report_id.report_template_end")
    def _compute_template_end(self):
        for rec in self:
            if rec.file_report_id and rec.file_report_id.report_template_end:
                rec.template_end = rec.file_report_id.report_template_end

    @api.depends("template_end")
    def _compute_template_end_rendered(self):
        for rec in self:
            rendered = ""
            if rec.template_end:
                try:
                    rendered = Template(rec.template_end).render(record=rec)
                except TemplateError as template_error:
                    rendered = (
                        '<p style="text-align:center;color:red;"><b>'
                        '<font style="font-size: 14px;">'
                        + self.env._("ERROR IN END TEMPLATE")
                        + "</font></b></p><p><br>"
                        + str(template_error)
                        + "</p>"
                    )
            rec.template_end_rendered = rendered

    # -------------------------
    # Reporting
    # -------------------------

    def action_print_selected_report(self):
        self.ensure_one()
        xmlid = (
            self.file_report_id.iractreportxml_id.xml_id
            if self.file_report_id
            else False
        )
        if not xmlid:
            raise exceptions.UserError(self.env._("No report has been selected."))
        return self.env.ref(xmlid).report_action(self)


class ResFilePartnerlink(models.Model):
    _name = "res.file.partnerlink"
    _description = "File Partnerlink"

    file_id = fields.Many2one(
        string="File_",
        comodel_name="res.file",
        required=True,
        index=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        string="Partner",
        comodel_name="res.partner",
        required=True,
        index=True,
        ondelete="restrict",
    )
    is_main = fields.Boolean(
        string="Primary", help="If checked, this partner will be the primary"
    )
    subject = fields.Char(string="Subject", related="file_id.subject")
    date_file = fields.Date(string="Discharge date", related="file_id.date_file")
    stage_id = fields.Many2one(string="Stage", related="file_id.stage_id")
    category_id = fields.Many2one(string="Category", related="file_id.category_id")


class ResFileFilelink(models.Model):
    _name = "res.file.filelink"
    _description = "File filelink"

    file_id = fields.Many2one(
        string="File_",
        comodel_name="res.file",
        required=True,
        index=True,
        ondelete="cascade",
    )
    related_file_id = fields.Many2one(
        string="Related File",
        comodel_name="res.file",
        required=True,
        ondelete="restrict",
    )
    related_file_subject = fields.Char(
        string="Subject", related="related_file_id.subject"
    )
    related_file_category_id = fields.Many2one(
        string="Category", related="related_file_id.category_id"
    )
