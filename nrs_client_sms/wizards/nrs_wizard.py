# -*- coding: utf-8 -*-
# 2021 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64
import requests
import json
import phonenumbers
import random
import string
from phonenumbers import carrier
from phonenumbers.phonenumberutil import number_type
from datetime import datetime
from jinja2 import Template, TemplateError
from lxml import etree


class NRSConfirmation(models.Model):
    _name = "nrs.confirmation"
    _description = "Response to SMS sent"

    response_code = fields.Text(
        string="Response",
        readonly=True)

    response_message = fields.Text(
        string="Response message",
        readonly=True)


class NRSWizard(models.Model):
    _name = "nrs.wizard"
    _description = "Wizard to send SMS through NRS service"

    def _get_default_template_id(self):
        context = self._context
        default_template_id = ""
        if context.get("mode") == "partner":
            default_template_id = self.env["ir.values"].get_default(
                "nrs.configuration", "default_partner_template_id")
        if context.get("mode") == "invoice":
            default_template_id = self.env["ir.values"].get_default(
                "nrs.configuration", "default_invoice_template_id")
        return default_template_id

    def _default_is_test_wizard(self):
        context = self._context
        is_test_wizard = False
        if context.get("mode") == "test":
            is_test_wizard = True
        return is_test_wizard

    def _get_default_sender(self):
        default_sender = self.env["ir.values"].get_default(
            "nrs.configuration", "default_sender")
        return default_sender

    def _default_allow_certify_sms(self):
        allow_certify_sms = self.env["ir.values"].get_default(
            "nrs.configuration", "allow_certify_sms")
        return allow_certify_sms

    def _default_allow_flash_sms(self):
        allow_flash_sms = self.env["ir.values"].get_default(
            "nrs.configuration", "allow_flash_sms")
        return allow_flash_sms

    def _default_wizard_mode(self):
        context = self._context
        mode = context.get("mode")
        return mode

    def _default_sms_encoding(self):
        sms_encoding = "gsm"
        return sms_encoding

    credentials = fields.Char(
        string="Credentials",
        compute="_compute_credentials")

    subject = fields.Char(
        string="Subject",
        size=100,
        help="Subject description (It is not sent, but it will be searchable "
             "in the tracking system.)")

    sender = fields.Char(
        string="From",
        default=_get_default_sender,
        compute="_compute_sender")

    sms_message = fields.Text(
        string="Message",
        help="One SMS for 160 chars in GSM or for 70 chars in UTF-16.")

    template_id = fields.Many2one(
        comodel_name="nrs.template",
        string="Template",
        default=_get_default_template_id,
        ondelete="set null")

    is_test_wizard = fields.Boolean(
        string="Test wizard",
        default=_default_is_test_wizard)

    certify = fields.Boolean(
        string="Certify",
        help="Certify the SMS. It will apply to all selected items. "
             "It has an additional cost.")

    sms_flash = fields.Boolean(
        string="Flash",
        help="The SMS appears directly on the device screen but it is not "
             "saved.")

    allow_certify_sms = fields.Boolean(
        default=_default_allow_certify_sms)

    allow_flash_sms = fields.Boolean(
        default=_default_allow_flash_sms)

    send_invoice_link = fields.Boolean(
        string="Send invoice link",
        help="It will generate a pdf and a link for each invoice. It slows "
             "down the process.")

    wizard_mode = fields.Char(
        default=_default_wizard_mode)

    number_of_characters = fields.Integer(
        string="Number of Characters",
        readonly=True,
    )

    sms_encoding = fields.Selection([
        ("gsm", "GSM 7"),
        ("utf-16", "UTF 16")],
        string="SMS encoding",
        default=_default_sms_encoding,
        readonly=True,
    )

    number_of_sms = fields.Integer(
        string="Number of SMS",
        readonly=True,
    )

    check_sms_message = fields.Text(
        string="Check Message",
        readonly=True,
        default=False,
    )

    @api.onchange("template_id")
    def _compute_template_id_fields(self):
        template = self.env["nrs.template"].browse(self.template_id.id)
        for record in self:
            record.subject = template.subject
            record.sms_message = template.template

    @api.onchange("send_invoice_link")
    def _compute_link_tracker_module(self):
        if not self.env.registry.get("link.tracker"):
            raise ValidationError(_("Link tracker is not installed."))

    @api.multi
    def _compute_sender(self):
        default_sender = self._get_default_sender()
        if not default_sender:
            raise ValidationError(_("No sender has been set."))
        for record in self:
            record.sender = default_sender

    @api.multi
    def _compute_credentials(self):
        service_user = self.env["ir.values"].get_default(
            "nrs.configuration", "service_user")
        service_passwd = self.env["ir.values"].get_default(
            "nrs.configuration", "service_passwd")

        if not service_user or not service_passwd:
            raise ValidationError(_("User or password not set."))
        else:
            self.credentials = \
                base64.b64encode(service_user + ":" + service_passwd)

    @api.multi
    def _compute_wizard_mode(self):
        context = self._context
        if context.get("mode") == "test":
            mode = "test"
        if context.get("mode") == "partner":
            mode = "partner"
        if context.get("mode") == "invoice":
            mode = "invoice"
        for record in self:
            record.wizard_mode = mode

    def _check_phone_number(self, phone_number):
        phone_number = phone_number.replace(" ", "").strip()
        if phone_number.startswith("+"):
            phone_number = phone_number.strip("+")
        if not phone_number.isdigit():
            raise ValidationError(_("Error in phone number, there are "
                                    "characters that are not digits."))
        # Reformat phone number to E.164
        reformated_phone_number = phonenumbers.format_number(
            phonenumbers.parse(phone_number, "ES"),
            phonenumbers.PhoneNumberFormat.E164)
        if (not carrier._is_mobile(
           number_type(phonenumbers.parse(reformated_phone_number, "ES")))):
            raise ValidationError(_("Error in phone number, or is not a "
                                    "mobile, or is not Spanish or does not "
                                    "have the correct format."))
        if reformated_phone_number.startswith("+"):
            reformated_phone_number = reformated_phone_number.strip("+")
        return reformated_phone_number

    def _generate_invoice_link(self, invoice_id):
        data = {"res_model": "account.invoice", "res_id": invoice_id,
                "mimetype": "application/pdf", "public": True}
        self.env["report"].get_pdf([invoice_id], "account.report_invoice",
                                   data=data)
        attachment = self.env["ir.attachment"].search(
            [("res_model", "=", "account.invoice"),
             ("res_id", "=", invoice_id)], order="write_date desc", limit=1)
        base_url = self.env["ir.config_parameter"].get_param("web.base.url")
        url_raw = base_url + "/web/login?redirect="
        url_download = \
            "/web/binary/download_sms_attachment/" + str(attachment.id)
        link_raw = self.env["link.tracker"].sudo().create(
            {"title": _("SMS Invoice PDF"), "url": base_url + url_download})
        url_redirect_pdf = url_raw + "/r/" + link_raw.code
        url = (self.env["link.tracker"].sudo().create(
            {"url": url_redirect_pdf}).short_url)
        return url

    def _generate_fake_invoice_link(self):
        base_url = self.env["ir.config_parameter"].get_param("web.base.url")
        random_link_code = \
            "".join(random.choice(string.ascii_letters) for _ in range(3))
        url = base_url + "/r/" + random_link_code
        return url

    def _get_confirmation_messages(self, response):
        response_code = response.status_code
        titles = {
            202: _("Accepted"),
            400: _("Bad request"),
            401: _("Unauthorized"),
            402: _("Payment required"),
            500: _("Internal server error"),
        }
        error_infos = {
            400: {
                102: _("Bad request - No valid recipients."),
                104: _("Bad request - Text message missing."),
                105: _("Bad request - Text message too long."),
                106: _("Bad request - Sender missing."),
                107: _("Bad request - Sender too long."),
                108: _("Bad request - No valid Datetime for send."),
                109: _("Bad request - Notification URL incorrect."),
                110: _("Bad request - Exceeded maximum parts allowed or "
                       "incorrect number of parts."),
                113: _("Bad request - Invalid coding."),
                120: _("Bad request - Invalid GUID."),
                121: _("Bad request - Invalid scheduled date."),
            },
            401: {
                103: _("Unauthorized - Username or password unknown."),
                111: _("Unauthorized - Not enough credits."),
            },
            402: {
                111: _("Payment required - Not enough credits."),
            },
            500: {
                122: _("Internal server error - Update error."),
                123: _("Internal server error - Delete error."),
            },
        }
        unknown_infos = {
            400: _("Bad request - Unknown error code."),
            401: _("Unauthorized - Unknown error code."),
            402: _("Payment required - Unknown error code."),
            500: _("Internal server error - Unknown error code."),
        }
        sms_confirmation = titles.get(response_code, _("Unknown error"))
        if response_code == 202:
            sms_confirmation_info = \
                _("Accepted - The message has been accepted for further "
                  "processing.")
        elif response_code in error_infos:
            response_data = json.loads(response.text)
            error_data = json.loads(json.dumps(response_data["error"]))
            error_code = error_data["code"]
            sms_confirmation_info = error_infos[response_code].get(
                error_code, unknown_infos[response_code])
        else:
            sms_confirmation_info = _("Unknown error")
        return sms_confirmation, sms_confirmation_info

    @api.multi
    def action_resolve_sms(self):
        self.ensure_one()
        context = dict(self._context, sms_preview=True)
        targets = self._get_send_targets(context)
        target = random.choice(targets)
        check_sms_message = self._render_sms_message(target)
        encoding = self.env["nrs.template"]._extract_encoding(
            check_sms_message)
        self.sms_encoding = encoding
        num_char = len(check_sms_message)
        self.number_of_characters = num_char
        self.number_of_sms = self.env[
            "nrs.template"]._calculate_number_of_sms(num_char, encoding)
        self.check_sms_message = check_sms_message
        if len(check_sms_message) > 1530:
            raise ValidationError(
                _("Number of characters must not exceed 1530"))
        return {
            "name": _("Compose SMS"),
            "type": "ir.actions.act_window",
            "res_model": "nrs.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "view_type": "form",
            "target": "new",
            "context": self._context,
        }

    @api.model
    def fields_view_get(self, view_id=None, view_type="form", toolbar=False,
                        submenu=False):
        context = self._context
        if context.get("mode") == "partner":
            context_filter = "[('type', '=', 'partner')]"
        elif context.get("mode") == "invoice":
            context_filter = "[('type', '=', 'invoice')]"
        else:
            context_filter = ""
        res = super(NRSWizard, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar,
            submenu=submenu)
        doc = etree.XML(res["arch"])
        for node in doc.xpath("//field[@name='template_id']"):
            node.set("domain", context_filter)
        res["arch"] = etree.tostring(doc)
        return res

    def _get_send_targets(self, context):
        mode = self.wizard_mode or "test"
        builder = getattr(self, "_get_targets_%s" % mode, None)
        if not builder:
            raise ValidationError(_("Unknown SMS mode: %s") % mode)
        targets = builder(context)
        if not targets:
            raise ValidationError(_("There are no items selected."))
        return targets

    def _get_partner_mobile(self, partner):
        if not partner.mobile:
            raise ValidationError(_("Partner %s does not have a "
                                    "mobile number" % partner.name))
        return partner.mobile

    def _resolve_phone(self, target):
        raw_phone = target.get("phone_override") or \
            self._get_partner_mobile(target["partner"])
        return self._check_phone_number(raw_phone)

    def _get_targets_test(self, context):
        phone = self.env["ir.values"].get_default(
            "nrs.configuration", "test_phone_number")
        if not phone:
            raise ValidationError(
                _("The phone number for testing has not been set."))
        target = {
            "partner": "",
            "phone_override": phone,
            "render_context": {
                "partner": "", "invoice": "", "datetime": datetime},
            "ref": "",
            "append_text": "",
            "tracking": {"partner_id": "", "invoice_id": ""},
        }
        return [target]

    def _get_targets_partner(self, context):
        targets = []
        partners = self.env["res.partner"].browse(context.get("active_ids"))
        for partner in partners:
            target = {
                "partner": partner,
                "render_context": {
                    "partner": partner, "invoice": "", "datetime": datetime},
                "ref": "",
                "append_text": "",
                "tracking": {"partner_id": partner.id, "invoice_id": ""},
            }
            targets.append(target)
        return targets

    def _get_targets_invoice(self, context):
        targets = []
        invoices = self.env["account.invoice"].browse(
            context.get("active_ids"))
        for invoice in invoices:
            partner = invoice.partner_id
            append_text = ""
            if self.send_invoice_link:
                if context.get("sms_preview"):
                    append_text = self._generate_fake_invoice_link()
                else:
                    append_text = self._generate_invoice_link(invoice.id)
            target = {
                "partner": partner,
                "render_context": {
                    "partner": partner, "invoice": invoice,
                    "datetime": datetime},
                "ref": invoice.number or "",
                "append_text": append_text,
                "tracking": {
                    "partner_id": partner.id, "invoice_id": invoice.id},
            }
            targets.append(target)
        return targets

    def _render_sms_message(self, target):
        if not self.sms_message:
            message = _("empty message")
        else:
            try:
                message = Template(self.sms_message).render(
                    **target["render_context"])
            except TemplateError as err:
                raise ValidationError(
                    _("Error resolving template: {}".format(err.message)))
            if target.get("append_text"):
                message += " " + target["append_text"]
            message = self.env[
                "nrs.template"]._escape_json_special_chars(message)
        return message

    def _post_sms(self, service_url, headers, sender, phone, message,
                  encoding, number_of_sms):
        data = json.dumps({
            "to": [phone],
            "from": sender,
            "message": message,
            "certified": self.certify,
            "encoding": encoding,
            "flash": self.sms_flash,
            "parts": number_of_sms, })
        response = None
        connection_error = ""
        try:
            response = requests.post(service_url, headers=headers, data=data)
        except requests.exceptions.RequestException as requests_error:
            connection_error = requests_error.message.message + "\n"
        return response, connection_error

    def _process_response(self, response, connection_error):
        if response is None:
            response_message = _("ERROR: no response")
            if connection_error:
                response_message += "\n" + connection_error
            return {
                "sms_confirmation": _("ERROR: no response"),
                "sms_confirmation_info": _("ERROR: no response"),
                "status_code": "error",
                "response_message": response_message,
                "name_id": "no-id",
                "certified": False,
            }
        sms_confirmation, sms_confirmation_info = \
            self._get_confirmation_messages(response)
        response_message = json.dumps(response.json(), indent=4)
        if "error" in response.text:
            name_id = "no-id"
            certified = False
        else:
            result = json.loads(response.text)["result"]
            name_id = result[0]["id"]
            certified = self.certify
        return {
            "sms_confirmation": sms_confirmation,
            "sms_confirmation_info": sms_confirmation_info,
            "status_code": response.status_code,
            "response_message": response_message,
            "name_id": name_id,
            "certified": certified,
        }

    def _get_confirmation_label(self, target, number_of_sms):
        subject = self.subject or _("No subject")
        parts = [subject, _("Num ") + str(number_of_sms)]
        if target.get("ref"):
            parts.append(target["ref"])
        if target.get("partner"):
            parts.append(target["partner"].name)
        return " - ".join(parts)

    def _format_confirmation_line(self, target, result, number_of_sms):
        label = self._get_confirmation_label(target, number_of_sms)
        line = result["sms_confirmation"] + " -- [" + label + "]"
        if result["certified"]:
            line += _(" [Certified] ")
        return line + "\n"

    def _format_response_block(self, target, result, number_of_sms, sender,
                               phone, counter, subject):
        is_certified = _("Yes") if result["certified"] else _("No")
        lines = [
            str(counter).zfill(4) + " " + "-" * 32,
            _("Subject: ") + subject,
            _("Sender: ") + sender,
            _("To: ") + phone,
        ]
        if target.get("partner"):
            lines.append(_("Partner: ") + target["partner"].name)
            lines.append(
                _("Confirmation: ") + result["sms_confirmation_info"])
        lines.append(_("Certified: ") + is_certified)
        lines.append(_("Number of SMS: ") + str(number_of_sms))
        lines.append(_("Response: ") + result["response_message"])
        return "\n".join(lines) + "\n\n"

    def _create_tracking(self, target, result, message, phone, number_of_sms,
                         service_url, nrs_user, sender, subject):
        tracking_data = {
            "name": result["name_id"],
            "nrs_url": service_url,
            "nrs_user": nrs_user,
            "user_id": self._uid,
            "sms_time_data": datetime.today(),
            "credentials": self.credentials,
            "subject": subject,
            "certified": result["certified"],
            "phone_number": phone,
            "sender": sender,
            "sms_message": message,
            "response_code": result["status_code"],
            "sms_confirmation": result["sms_confirmation"],
            "sms_confirmation_info": result["sms_confirmation_info"],
            "response_message": result["response_message"],
            "number_of_sms": number_of_sms, }
        tracking_data.update(target["tracking"])
        self.env["nrs.tracking"].create(tracking_data)

    @api.multi
    def send_sms_action(self, context):
        self.ensure_one()
        service_url = self.env["ir.values"].get_default(
            "nrs.configuration", "service_url")
        nrs_user = self.env["ir.values"].get_default(
            "nrs.configuration", "service_user")
        sender = self.sender
        subject = self.subject or _("No subject")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Basic " + self.credentials, }
        targets = self._get_send_targets(context)
        sms_confirmations = ""
        response_messages = ""
        counter = 0
        for target in targets:
            counter += 1
            phone = self._resolve_phone(target)
            message = self._render_sms_message(target)
            if len(message) > 1530:
                raise ValidationError(
                    _("Number of characters must not exceed 1530"))
            encoding = self.env["nrs.template"]._extract_encoding(message)
            number_of_sms = self.env[
                "nrs.template"]._calculate_number_of_sms(
                    len(message), encoding)
            response, connection_error = self._post_sms(
                service_url, headers, sender, phone, message, encoding,
                number_of_sms)
            result = self._process_response(response, connection_error)
            sms_confirmations += self._format_confirmation_line(
                target, result, number_of_sms)
            response_messages += self._format_response_block(
                target, result, number_of_sms, sender, phone, counter,
                subject)
            self._create_tracking(
                target, result, message, phone, number_of_sms, service_url,
                nrs_user, sender, subject)
        return {
            "name": _("SMS confirmation"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "nrs.confirmation",
            "type": "ir.actions.act_window",
            "context": {
                "default_response_code": "%s" % sms_confirmations,
                "default_response_message": "%s" % response_messages,
            },
            "target": "new",
        }
