# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import base64
from io import BytesIO

from odoo import api, fields, models
from odoo.exceptions import UserError

try:
    import qrcode
except ImportError:  # pragma: no cover
    qrcode = None


class DecaVersion(models.Model):
    _name = "deca.version"
    _description = "DECA Issued Version (immutable)"
    _order = "deca_id, sequence desc"

    deca_id = fields.Many2one(
        "deca.document",
        string="DECA",
        required=True,
        ondelete="restrict",
        index=True,
    )
    company_id = fields.Many2one("res.company", index=True)
    sequence = fields.Integer(required=True, default=1)
    previous_version_id = fields.Many2one(
        "deca.version",
        ondelete="restrict",
    )
    reason = fields.Char(string="Revision Reason")
    issued_at = fields.Datetime(required=True)
    author_id = fields.Many2one("res.users", string="Issued By", required=True)
    access_token = fields.Char(required=True, index=True, copy=False)
    sha256 = fields.Char(string="SHA-256", readonly=True)
    pdf_attachment_id = fields.Many2one("ir.attachment", string="PDF File")
    pdf_filename = fields.Char()

    deca_number = fields.Char(string="Document Number")
    loading_name = fields.Char(string="Loading Party")
    loading_vat = fields.Char(string="Loading Party VAT")
    loading_address = fields.Char()
    carrier_name = fields.Char(string="Carrier")
    carrier_vat = fields.Char(string="Carrier VAT")
    origin = fields.Char()
    destination = fields.Char()
    transport_date = fields.Date()
    goods_description = fields.Text()
    weight_kg = fields.Float(string="Weight (kg)")
    alternative_measure = fields.Char()
    vehicle_plate = fields.Char()
    trailer_plate = fields.Char()
    special_authorization = fields.Char()
    observations = fields.Text()
    driver_name = fields.Char()
    driver_vat = fields.Char(string="Driver VAT")
    line_ids = fields.One2many(
        "deca.version.line",
        "version_id",
        string="Goods Lines",
    )
    public_url = fields.Char(compute="_compute_public_url")
    qr_image = fields.Binary(compute="_compute_qr_image", string="QR Code")

    @api.depends("access_token")
    def _compute_public_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param(
            "web.base.url"
        )
        for version in self:
            if version.access_token:
                version.public_url = "%s/deca/%s" % (
                    base_url,
                    version.access_token,
                )
            else:
                version.public_url = False

    @api.depends("public_url")
    def _compute_qr_image(self):
        for version in self:
            # pylint: disable=protected-access
            version.qr_image = version._build_qr_image(version.public_url)

    def _build_qr_image(self, value):
        self.ensure_one()
        if not value or qrcode is None:
            return False
        img = qrcode.make(value, box_size=4, border=2)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue())

    def write(self, vals):
        if not self.env.context.get("deca_version_commit"):
            raise UserError(
                self.env._("Issued DECA versions cannot be modified.")
            )
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_never(self):
        raise UserError(
            self.env._("Issued DECA versions cannot be deleted.")
        )


class DecaVersionLine(models.Model):
    _name = "deca.version.line"
    _description = "DECA Version Goods Line (immutable)"

    version_id = fields.Many2one(
        "deca.version",
        required=True,
        ondelete="cascade",
        index=True,
    )
    name = fields.Char(string="Description")
    quantity = fields.Float()
    uom_name = fields.Char(string="Unit of Measure")
    weight_kg = fields.Float(string="Weight (kg)")

    def write(self, vals):
        if not self.env.context.get("deca_version_commit"):
            raise UserError(
                self.env._("Issued DECA version lines cannot be modified.")
            )
        return super().write(vals)
