# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_AGENDA_VOTE_MODE_MANUAL_MULTI = "manual_multi"


class AssemblyAgendaOption(models.Model):
    _name = "assembly.agenda.option"
    _description = "Assembly agenda option"
    _order = "agenda_id, sequence, id"

    agenda_id = fields.Many2one(
        "assembly.agenda",
        string="Agenda item",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    name = fields.Char(
        string="Choice",
        required=True,
        translate=True,
        help="Label for this choice as it appears on the ballot.",
    )
    sequence = fields.Integer(default=10)
    manual_vote_count = fields.Integer(
        string="Votes",
        default=0,
        help=(
            "Final total votes cast for this choice. "
            "Enter aggregate counts only; votes are not recorded per attendee."
        ),
    )

    @api.constrains("manual_vote_count")
    def _check_manual_vote_count_nonnegative(self):
        for rec in self:
            if rec.manual_vote_count < 0:
                raise ValidationError(
                    self.env._("Votes per option cannot be negative.")
                )

    def _revalidate_parent_agenda_manual_multi(self):
        agendas = self.mapped("agenda_id").filtered(
            lambda a: a.agenda_vote_mode == _AGENDA_VOTE_MODE_MANUAL_MULTI
        )
        for agenda in agendas:
            agenda._validate_manual_expected_total_for_mode()

    @api.model_create_multi
    def create(self, vals_list):
        agenda_ids = [v.get("agenda_id") for v in vals_list if v.get("agenda_id")]
        if agenda_ids:
            self.env["assembly.agenda"].browse(agenda_ids).mapped(
                "assembly_id"
            )._assembly_ensure_not_closed_for_related_changes()
        records = super().create(vals_list)
        records._revalidate_parent_agenda_manual_multi()
        return records

    def write(self, vals):
        self.mapped(
            "agenda_id.assembly_id"
        )._assembly_ensure_not_closed_for_related_changes()
        res = super().write(vals)
        if any(k in vals for k in ("manual_vote_count", "agenda_id")):
            self._revalidate_parent_agenda_manual_multi()
        return res

    def unlink(self):
        self.mapped(
            "agenda_id.assembly_id"
        )._assembly_ensure_not_closed_for_related_changes()
        agendas = self.mapped("agenda_id")
        res = super().unlink()
        agendas.filtered(
            lambda a: a.agenda_vote_mode == _AGENDA_VOTE_MODE_MANUAL_MULTI
        )._validate_manual_expected_total_for_mode()
        return res

    @api.constrains("agenda_id")
    def _check_agenda_allows_ballot_options(self):
        """Keep in sync with ``assembly.agenda`` option/mode coherence (O2M inverse)."""
        for rec in self:
            if rec.agenda_id.agenda_vote_mode != _AGENDA_VOTE_MODE_MANUAL_MULTI:
                raise ValidationError(
                    self.env._(
                        "Ballot options are only allowed in manual multi-option mode."
                    )
                )

    _sql_constraints = [
        (
            "assembly_agenda_option_agenda_sequence_uniq",
            "UNIQUE(agenda_id, sequence)",
            "Ballot option sequence must be unique per agenda item.",
        ),
    ]
