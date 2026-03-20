# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AssemblyAttendee(models.Model):
    _name = "assembly.attendee"
    _description = "Assembly attendee"
    _order = "assembly_id, partner_id"

    assembly_id = fields.Many2one(
        "assembly.assembly",
        string="Assembly",
        required=True,
        ondelete="cascade",
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required=True,
        ondelete="cascade",
        index=True,
        help="Partner with vote rights (member).",
    )
    participant_partner_id = fields.Many2one(
        "res.partner",
        string="Participant",
        ondelete="set null",
        index=True,
        help=(
            "Who actually attends (default: partner). "
            "Set to representative when applicable."
        ),
    )
    attendance_type = fields.Selection(
        [("present", "Present"), ("remote", "Remote")],
        string="Attendance type",
        default="present",
    )
    date_register = fields.Datetime(string="Registration date")
    attendee_vote_ids = fields.One2many(
        "assembly.attendee.vote",
        "attendee_id",
        string="Votes by type",
    )
    attendee_state = fields.Selection(
        [
            ("registered", "Registered"),
            ("confirmed", "Confirmed"),
            ("absent", "Absent"),
        ],
        string="State",
        default="registered",
        required=True,
    )
    attendance_signature = fields.Binary(string="Signature")
    attendance_notes = fields.Text(string="Attendance notes")
    attendance_url = fields.Char(
        string="Attendance URL",
        compute="_compute_attendance_url",
        help="URL to open this attendee form (e.g. for QR code).",
    )
    partner_vat = fields.Char(
        string="TIN",
        related="partner_id.vat",
        readonly=True,
    )
    total_votes = fields.Float(
        string="Total votes",
        compute="_compute_total_votes",
    )
    count_attendee_votes = fields.Integer(
        string="Vote types count",
        compute="_compute_count_attendee_votes",
    )

    @api.depends("attendee_vote_ids")
    def _compute_count_attendee_votes(self):
        for rec in self:
            rec.count_attendee_votes = len(rec.attendee_vote_ids)

    def action_open_assembly(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Assembly"),
            "res_model": "assembly.assembly",
            "view_mode": "form",
            "res_id": self.assembly_id.id,
            "target": "current",
        }

    def action_open_attendee_votes(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Votes by type"),
            "res_model": "assembly.attendee.vote",
            "view_mode": "list",
            "domain": [("attendee_id", "=", self.id)],
            "context": {"default_attendee_id": self.id},
        }

    _sql_constraints = [
        (
            "assembly_partner_uniq",
            "UNIQUE(assembly_id, partner_id)",
            "Partner can only be registered once per assembly.",
        ),
    ]

    @api.depends("assembly_id")
    def _compute_attendance_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for rec in self:
            if rec.id and base_url:
                rec.attendance_url = (
                    f"{base_url}/web#model=assembly.attendee&id={rec.id}&view_type=form"
                )
            else:
                rec.attendance_url = ""

    @api.depends("attendee_vote_ids", "attendee_vote_ids.attendee_vote_total")
    def _compute_total_votes(self):
        for rec in self:
            rec.total_votes = sum(rec.attendee_vote_ids.mapped("attendee_vote_total"))

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id and not self.participant_partner_id:
            self.participant_partner_id = self.partner_id

    def action_confirm(self):
        for rec in self:
            if rec.attendee_state != "registered":
                continue
            rec.attendee_state = "confirmed"
            rec.date_register = fields.Datetime.now()
            rec.recompute_votes()

    def action_mark_absent(self):
        for rec in self:
            rec.attendee_state = "absent"
            rec.recompute_votes()

    def recompute_votes(self):
        """Create or update attendee_vote_ids from partner.vote and delegations."""
        for attendee in self:
            assembly = attendee.assembly_id
            vote_types = assembly.vote_type_ids
            partner_vote_model = self.env["partner.vote"]
            vote_owner = attendee.partner_id  # votes belong to the member (partner_id)
            for vote_type in vote_types:
                pv = partner_vote_model.search(
                    [
                        ("partner_id", "=", vote_owner.id),
                        ("vote_type_id", "=", vote_type.id),
                    ],
                    limit=1,
                )
                own = pv.vote_count_display if pv else 0.0
                out = 0.0
                in_ = 0.0
                if attendee.attendee_state == "confirmed":
                    out = self._delegated_out_for_type(attendee, vote_type)
                    in_ = self._delegated_in_for_type(attendee, vote_type)
                av = self.env["assembly.attendee.vote"].search(
                    [
                        ("attendee_id", "=", attendee.id),
                        ("vote_type_id", "=", vote_type.id),
                    ],
                    limit=1,
                )
                vals = {
                    "own_votes": own,
                    "delegated_out_votes": out,
                    "delegated_in_votes": in_,
                }
                if av:
                    av.sudo().write(vals)
                else:
                    self.env["assembly.attendee.vote"].sudo().create(
                        {
                            "attendee_id": attendee.id,
                            "vote_type_id": vote_type.id,
                            **vals,
                        }
                    )

    def _delegated_out_for_type(self, attendee, vote_type):
        """Votes this attendee (vote owner) delegated out for this type."""
        vote_owner = attendee.partner_id
        delegations = self.env["assembly.delegation"].search(
            [
                ("assembly_id", "=", attendee.assembly_id.id),
                ("partner_id", "=", vote_owner.id),
                ("delegation_state", "=", "confirmed"),
            ]
        )
        total = 0.0
        for d in delegations:
            effective = d.vote_type_ids or attendee.assembly_id.vote_type_ids
            if vote_type in effective:
                pv = self.env["partner.vote"].search(
                    [
                        ("partner_id", "=", vote_owner.id),
                        ("vote_type_id", "=", vote_type.id),
                    ],
                    limit=1,
                )
                if pv:
                    total += pv.vote_count_display
        return total

    def _delegated_in_for_type(self, attendee, vote_type):
        """Votes this attendee (vote owner) received by delegation for this type."""
        vote_owner = attendee.partner_id
        delegations = self.env["assembly.delegation"].search(
            [
                ("assembly_id", "=", attendee.assembly_id.id),
                ("delegate_partner_id", "=", vote_owner.id),
                ("delegation_state", "=", "confirmed"),
            ]
        )
        total = 0.0
        for d in delegations:
            effective = d.vote_type_ids or attendee.assembly_id.vote_type_ids
            if vote_type in effective:
                pv = self.env["partner.vote"].search(
                    [
                        ("partner_id", "=", d.partner_id.id),
                        ("vote_type_id", "=", vote_type.id),
                    ],
                    limit=1,
                )
                if pv:
                    total += pv.vote_count_display
        return total
