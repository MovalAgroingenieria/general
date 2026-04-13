# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import UserError


class AssemblyCommunicationSendWizard(
    models.TransientModel
):  # pylint: disable=no-wizard-in-models
    _name = "assembly.communication.send.wizard"
    _description = "Send assembly outbound emails (one per recipient)"

    assembly_id = fields.Many2one(
        "assembly.assembly",
        string="Assembly",
        required=True,
        ondelete="cascade",
        check_company=True,
    )
    primary_message_kind = fields.Selection(
        [
            ("publication", "Publication / call"),
            ("ballot_intro", "Member ballot"),
            ("delegation", "Delegation"),
        ],
        string="Main message",
        required=True,
        default="publication",
    )
    recipient_mode = fields.Selection(
        [
            ("single", "One selected attendee"),
            ("all", "Each matching attendee (one email each)"),
        ],
        string="Recipients",
        required=True,
        default="all",
    )
    recipient_audience = fields.Selection(
        [
            ("all", "All attendees"),
            ("confirmed", "Attended (confirmed) only"),
            ("registered", "Listed only — not finalized"),
        ],
        string="Audience",
        default="all",
        required=True,
        help="Only used when sending to each matching attendee. Partners without an email are skipped.",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Recipient",
        domain="[('id', 'in', allowed_partner_ids)]",
    )
    allowed_partner_ids = fields.Many2many(
        "res.partner",
        compute="_compute_allowed_partner_ids",
    )
    email_recipient_count = fields.Integer(
        string="Recipients (preview)",
        compute="_compute_email_recipient_preview",
    )
    email_recipient_hint = fields.Char(
        string="Send preview",
        compute="_compute_email_recipient_preview",
    )
    attach_publication_pdf = fields.Boolean(
        string="Publication PDF",
        default=False,
        help="Assembly publication / convocation PDF (same file for every recipient).",
    )
    attach_generic_ballot_pdf = fields.Boolean(
        string="Ballot PDF (merged, all attendees)",
        default=False,
        help="Single PDF with every member ballot in sequence. Same attachment on each email when enabled; use together with nominative only if you intend both.",
    )
    attach_nominative_ballot_pdf = fields.Boolean(
        string="Nominative ballot PDF",
        default=False,
        help="Personalized member ballot for this recipient only (requires an attendee row for that partner).",
    )
    attach_delegation_pdf = fields.Boolean(
        string="Delegation PDF",
        default=False,
        help="Vote delegation register for the assembly (same file for every recipient).",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        kind = self.env.context.get("default_primary_message_kind") or res.get(
            "primary_message_kind"
        )
        if not kind:
            kind = "publication"
        attach_keys = (
            "attach_publication_pdf",
            "attach_generic_ballot_pdf",
            "attach_nominative_ballot_pdf",
            "attach_delegation_pdf",
        )
        profile = {
            "publication": (True, False, False, False),
            "ballot_intro": (False, False, True, False),
            "delegation": (False, False, False, True),
        }
        values = profile.get(kind, (False, False, False, False))
        for key, val in zip(attach_keys, values):
            if not fields_list or key in fields_list:
                res[key] = val
        return res

    @api.depends("assembly_id")
    def _compute_allowed_partner_ids(self):
        Attendee = self.env["assembly.attendee"]
        for wiz in self:
            if not wiz.assembly_id:
                wiz.allowed_partner_ids = False
                continue
            attendees = Attendee.search([("assembly_id", "=", wiz.assembly_id.id)])
            wiz.allowed_partner_ids = attendees.mapped("partner_id")

    @api.depends(
        "assembly_id",
        "recipient_mode",
        "recipient_audience",
        "partner_id",
    )
    def _compute_email_recipient_preview(self):
        svc = self.env["assembly.mail.communication"]
        Attendee = self.env["assembly.attendee"]
        for wiz in self:
            asm = wiz.assembly_id
            if not asm:
                wiz.email_recipient_count = 0
                wiz.email_recipient_hint = ""
                continue
            if wiz.recipient_mode == "single":
                p = wiz.partner_id
                if (
                    p
                    and (p.email or "").strip()
                    and Attendee.search_count(
                        [
                            ("assembly_id", "=", asm.id),
                            ("partner_id", "=", p.id),
                        ],
                        limit=1,
                    )
                ):
                    wiz.email_recipient_count = 1
                    wiz.email_recipient_hint = wiz.env._(
                        "One email to %(email)s.",
                        email=p.email,
                    )
                else:
                    wiz.email_recipient_count = 0
                    wiz.email_recipient_hint = wiz.env._(
                        "Choose an attendee with an email address."
                    )
            else:
                partners = svc._resolve_recipient_partners(
                    asm,
                    recipient_mode="all",
                    audience=wiz.recipient_audience,
                    single_partner=False,
                )
                n = len(partners)
                wiz.email_recipient_count = n
                wiz.email_recipient_hint = wiz.env._(
                    "%(count)d recipient(s): one separate email each; nominative attachments match the addressee.",
                    count=n,
                )

    @api.onchange("primary_message_kind")
    def _onchange_primary_message_kind_attach_defaults(self):
        if self.primary_message_kind == "publication":
            self.attach_publication_pdf = True
            self.attach_generic_ballot_pdf = False
            self.attach_nominative_ballot_pdf = False
            self.attach_delegation_pdf = False
        elif self.primary_message_kind == "ballot_intro":
            self.attach_publication_pdf = False
            self.attach_generic_ballot_pdf = False
            self.attach_nominative_ballot_pdf = True
            self.attach_delegation_pdf = False
        else:
            self.attach_publication_pdf = False
            self.attach_generic_ballot_pdf = False
            self.attach_nominative_ballot_pdf = False
            self.attach_delegation_pdf = True

    def _attachment_options_dict(self):
        self.ensure_one()
        return {
            "attach_publication_pdf": self.attach_publication_pdf,
            "attach_generic_ballot_pdf": self.attach_generic_ballot_pdf,
            "attach_nominative_ballot_pdf": self.attach_nominative_ballot_pdf,
            "attach_delegation_pdf": self.attach_delegation_pdf,
        }

    def _document_summary_labels(self):
        self.ensure_one()
        labels = []
        if self.attach_publication_pdf:
            labels.append(self.env._("Publication PDF"))
        if self.attach_generic_ballot_pdf:
            labels.append(self.env._("Ballot PDF (merged)"))
        if self.attach_nominative_ballot_pdf:
            labels.append(self.env._("Nominative ballot PDF"))
        if self.attach_delegation_pdf:
            labels.append(self.env._("Delegation PDF"))
        return labels

    def action_send_communication(self):
        self.ensure_one()
        assembly = self.assembly_id
        service = self.env["assembly.mail.communication"]
        single = self.partner_id if self.recipient_mode == "single" else False
        if self.recipient_mode == "single":
            if not single or not single.exists():
                raise UserError(self.env._("Select one attendee as the recipient."))
            if not (single.email or "").strip():
                raise UserError(
                    self.env._("The selected contact has no email address.")
                )
        partners = service._resolve_recipient_partners(
            assembly,
            recipient_mode=self.recipient_mode,
            audience=self.recipient_audience,
            single_partner=single,
        )
        if not partners:
            raise UserError(
                self.env._(
                    "No recipients with an email address were found for the selected options."
                )
            )
        if self.recipient_mode == "single" and len(partners) != 1:
            raise UserError(
                self.env._("The selected partner is not an attendee of this assembly.")
            )
        attach_opts = self._attachment_options_dict()
        sent, skipped, errors = service.send_to_partners(
            assembly,
            partners,
            primary_kind=self.primary_message_kind,
            attachment_options=attach_opts,
        )
        kind_label = {
            "publication": self.env._("Publication / call"),
            "ballot_intro": self.env._("Member ballot"),
            "delegation": self.env._("Delegation"),
        }.get(self.primary_message_kind, self.primary_message_kind)
        doc_part = ", ".join(self._document_summary_labels()) or self.env._("none")
        summary = self.env._(
            "Outbound email batch: %(kind)s. Sent: %(sent)d, skipped (no email or "
            "error): %(skip)d. Attachments included: %(docs)s.",
            kind=kind_label,
            sent=sent,
            skip=skipped,
            docs=doc_part,
        )
        if errors:
            detail = "; ".join(
                self.env._("Partner %(pid)s: %(err)s", pid=pid, err=err)
                for pid, err in errors[:10]
            )
            summary = self.env._(
                "%(summary)s Issues: %(detail)s", summary=summary, detail=detail
            )
        assembly.sudo().message_post(
            body=summary,
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Communications sent"),
                "message": self.env._(
                    "%(sent)d message(s) queued or sent. %(skip)d skipped.",
                    sent=sent,
                    skip=skipped,
                ),
                "type": "success",
                "sticky": False,
            },
        }
