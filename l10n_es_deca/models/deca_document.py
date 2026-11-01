# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import base64
import hashlib
import secrets

from odoo import api, fields, models
from odoo.exceptions import UserError

STATE_SELECTION = [
    ("draft", "Draft"),
    ("issued", "Issued"),
    ("cancelled", "Cancelled"),
]

VERSION_SNAPSHOT_FIELDS = [
    "loading_address",
    "origin",
    "destination",
    "transport_date",
    "goods_description",
    "weight_kg",
    "alternative_measure",
    "vehicle_plate",
    "trailer_plate",
    "special_authorization",
    "observations",
]


class DecaDocument(models.Model):
    _name = "deca.document"
    _description = "Transport Control Document (DECA)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "transport_date desc, id desc"

    name = fields.Char(
        default="/",
        copy=False,
        readonly=True,
        index=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=STATE_SELECTION,
        default="draft",
        required=True,
        copy=False,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    loading_partner_id = fields.Many2one(
        "res.partner",
        string="Loading Party",
        tracking=True,
    )
    loading_name = fields.Char(string="Loading Party Name", tracking=True)
    loading_vat = fields.Char(string="Loading Party VAT", tracking=True)
    loading_address = fields.Char(tracking=True)
    carrier_partner_id = fields.Many2one(
        "res.partner",
        string="Effective Carrier",
        tracking=True,
    )
    carrier_name = fields.Char(tracking=True)
    carrier_vat = fields.Char(string="Carrier VAT", tracking=True)
    origin = fields.Char(tracking=True)
    destination = fields.Char(tracking=True)
    transport_date = fields.Date(
        default=fields.Date.context_today,
        tracking=True,
    )
    goods_description = fields.Text(tracking=True)
    weight_kg = fields.Float(string="Weight (kg)", tracking=True)
    alternative_measure = fields.Char(tracking=True)
    vehicle_plate = fields.Char(tracking=True)
    trailer_plate = fields.Char(tracking=True)
    special_authorization = fields.Char(tracking=True)
    observations = fields.Text(tracking=True)
    driver_partner_id = fields.Many2one(
        "res.partner",
        string="Driver",
        tracking=True,
    )
    driver_name = fields.Char(tracking=True)
    driver_vat = fields.Char(string="Driver VAT", tracking=True)
    line_ids = fields.One2many(
        "deca.line",
        "deca_id",
        string="Goods Lines",
    )
    issued_date = fields.Datetime(readonly=True, copy=False)
    version_ids = fields.One2many(
        "deca.version",
        "deca_id",
    )
    current_version_id = fields.Many2one(
        "deca.version",
        copy=False,
        readonly=True,
    )
    version_count = fields.Integer(
        compute="_compute_version_count",
    )
    pending_revision_reason = fields.Char(copy=False)
    public_url = fields.Char(
        related="current_version_id.public_url",
        string="Public URL",
    )
    qr_image = fields.Binary(
        related="current_version_id.qr_image",
        string="QR Code",
    )

    @api.onchange("loading_partner_id")
    def _onchange_loading_partner_id(self):
        partner = self.loading_partner_id
        if partner:
            self.loading_name = partner.name
            self.loading_vat = partner.vat
            self.loading_address = partner.contact_address

    @api.onchange("carrier_partner_id")
    def _onchange_carrier_partner_id(self):
        partner = self.carrier_partner_id
        if partner:
            self.carrier_name = partner.name
            self.carrier_vat = partner.vat

    @api.onchange("driver_partner_id")
    def _onchange_driver_partner_id(self):
        partner = self.driver_partner_id
        if partner:
            self.driver_name = partner.name
            self.driver_vat = partner.vat

    @api.depends("version_ids")
    def _compute_version_count(self):
        # pylint: disable=protected-access
        version_data = self.env["deca.version"]._read_group(
            [("deca_id", "in", self.ids)],
            ["deca_id"],
            ["__count"],
        )
        mapped_count = {deca.id: count for deca, count in version_data}
        for record in self:
            record.version_count = mapped_count.get(record.id, 0)

    def _get_loading_display_name(self):
        self.ensure_one()
        return self.loading_partner_id.name or self.loading_name

    def _get_loading_display_vat(self):
        self.ensure_one()
        return self.loading_partner_id.vat or self.loading_vat

    def _get_carrier_display_name(self):
        self.ensure_one()
        return self.carrier_partner_id.name or self.carrier_name

    def _get_carrier_display_vat(self):
        self.ensure_one()
        return self.carrier_partner_id.vat or self.carrier_vat

    def _get_driver_display_name(self):
        self.ensure_one()
        return self.driver_partner_id.name or self.driver_name

    def _get_driver_display_vat(self):
        self.ensure_one()
        return self.driver_partner_id.vat or self.driver_vat

    def _build_version_vals(self, reason):
        self.ensure_one()
        vals = {
            "deca_id": self.id,
            "sequence": len(self.version_ids) + 1,
            "reason": reason,
            "previous_version_id": self.current_version_id.id or False,
            "access_token": secrets.token_urlsafe(32),
            "issued_at": fields.Datetime.now(),
            "author_id": self.env.user.id,
            "company_id": self.company_id.id,
            "deca_number": self.name,
            "loading_name": self._get_loading_display_name(),
            "loading_vat": self._get_loading_display_vat(),
            "carrier_name": self._get_carrier_display_name(),
            "carrier_vat": self._get_carrier_display_vat(),
            "driver_name": self._get_driver_display_name(),
            "driver_vat": self._get_driver_display_vat(),
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "name": line.name,
                        "quantity": line.quantity,
                        "uom_name": line.uom_name,
                        "weight_kg": line.weight_kg,
                    },
                )
                for line in self.line_ids
            ],
        }
        for field_name in VERSION_SNAPSHOT_FIELDS:
            vals[field_name] = self[field_name]
        return vals

    def _render_version_pdf(self, version):
        report = self.env.ref(
            "l10n_es_deca.action_report_deca_version"
        ).sudo()
        # pylint: disable=protected-access
        pdf_content, _unused = report._render_qweb_pdf(
            "l10n_es_deca.report_deca_version", res_ids=version.ids
        )
        return pdf_content

    def _create_version(self, reason):
        self.ensure_one()
        version = (
            self.env["deca.version"]
            .with_context(deca_version_commit=True)
            .create(self._build_version_vals(reason))
        )
        pdf_content = self._render_version_pdf(version)
        sha256 = hashlib.sha256(pdf_content).hexdigest()
        filename = "DECA-%s-v%s.pdf" % (self.name, version.sequence)
        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "res_model": "deca.version",
                "res_id": version.id,
                "type": "binary",
                "mimetype": "application/pdf",
                "datas": base64.b64encode(pdf_content),
            }
        )
        version.with_context(deca_version_commit=True).write(
            {
                "pdf_attachment_id": attachment.id,
                "pdf_filename": filename,
                "sha256": sha256,
            }
        )
        return version

    def _check_issue_values(self):
        self.ensure_one()
        checks = [
            (self._get_loading_display_name(), self.env._("Loading party name")),
            (self._get_loading_display_vat(), self.env._("Loading party VAT")),
            (
                self._get_carrier_display_name(),
                self.env._("Effective carrier name"),
            ),
            (
                self._get_carrier_display_vat(),
                self.env._("Effective carrier VAT"),
            ),
            (self.transport_date, self.env._("Transport date")),
            (self.origin, self.env._("Origin")),
            (self.destination, self.env._("Destination")),
            (self.goods_description, self.env._("Nature of the goods")),
            (
                self.weight_kg or self.alternative_measure,
                self.env._("Weight or alternative measure"),
            ),
            (self.vehicle_plate, self.env._("Vehicle plate")),
            (self._get_driver_display_name(), self.env._("Driver name")),
            (self._get_driver_display_vat(), self.env._("Driver VAT")),
        ]
        missing = [label for value, label in checks if not value]
        if missing:
            raise UserError(
                self.env._(
                    "The DECA cannot be issued. Missing data: %(fields)s",
                    fields=", ".join(missing),
                )
            )

    def action_issue(self):
        for record in self:
            if record.state == "issued":
                continue
            record._check_issue_values()  # pylint: disable=protected-access
            if record.name in (False, "/"):
                record.name = (
                    self.env["ir.sequence"].next_by_code("deca.document") or "/"
                )
            is_revision = bool(record.version_ids)
            reason = record.pending_revision_reason if is_revision else False
            if is_revision and not reason:
                raise UserError(
                    self.env._(
                        "A revision reason is required before re-issuing "
                        "this DECA."
                    )
                )
            version = record._create_version(  # pylint: disable=protected-access
                reason
            )
            record.write(
                {
                    "state": "issued",
                    "issued_date": fields.Datetime.now(),
                    "current_version_id": version.id,
                    "pending_revision_reason": False,
                }
            )
        return True

    def action_open_revise_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Revise DECA"),
            "res_model": "deca.revise",
            "view_mode": "form",
            "target": "new",
            "context": {"default_deca_id": self.id},
        }

    def action_cancel(self):
        self.write({"state": "cancelled"})
        return True

    def action_print_report(self):
        self.ensure_one()
        if self.state == "draft":
            self.action_issue()
        attachment = self.current_version_id.pdf_attachment_id
        if not attachment:
            raise UserError(
                self.env._("The DECA has no archived PDF to print.")
            )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "new",
        }

    def action_view_versions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("DECA Versions"),
            "res_model": "deca.version",
            "domain": [("deca_id", "=", self.id)],
            "view_mode": "list,form",
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_except_issued(self):
        if any(record.version_ids for record in self):
            raise UserError(
                self.env._(
                    "DECA documents with issued versions cannot be deleted."
                )
            )
