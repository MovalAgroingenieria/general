# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import AccessError, MissingError, UserError

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    primary_entity_id = fields.Many2one(
        comodel_name="res.partner",
        string="Primary Entity",
        required=False,
        readonly=False,
        store=True,
        index=True,
        copy=True,
        ondelete="restrict",
        domain=[("is_primary_entity", "=", True)],
        help="Primary entity of the source census when this invoice line was "
        "created, or the entity manually assigned to an eligible journal "
        "item. Later changes to the census do not update this value.",
    )
    primary_entity_manual_allowed = fields.Boolean(
        compute="_compute_primary_entity_manual_allowed",
        help="Whether the primary entity can be assigned manually to this item.",
    )

    @api.depends(
        "billable_item_model",
        "billable_item_res_id",
        "display_type",
        "tax_line_id",
        "account_type",
        "payment_id",
        "statement_line_id",
    )
    def _compute_primary_entity_manual_allowed(self):
        source_models = self._get_primary_entity_source_fields()
        for line in self:
            from_census = line.billable_item_model in source_models and bool(
                line.billable_item_res_id
            )
            line.primary_entity_manual_allowed = bool(
                not from_census
                and line.display_type == "product"
                and not line.tax_line_id
                and line.account_type
                not in (
                    "asset_receivable",
                    "liability_payable",
                )
                and not line.payment_id
                and not line.statement_line_id
            )

    @api.model
    def _get_primary_entity_source_fields(self):
        """Model -> ordered relational paths; extend this hook for new sources."""
        return {
            "general.entity.census.line": ("primary_partner_id",),
            "general.entity.census.additional": (
                "primary_partner_id",
                "census_line_id.primary_partner_id",
            ),
        }

    @api.model
    def _get_primary_entity_invoice_values(self, vals_list, source_fields):
        """Select eligible values before creation, fetching accounting data in bulk."""
        candidates = []
        for vals in vals_list:
            # Explicit False is also a historical value when copying a line.
            if "primary_entity_id" in vals:
                continue
            if vals.get("billable_item_model") not in source_fields:
                continue
            res_id = vals.get("billable_item_res_id")
            if not isinstance(res_id, int) or isinstance(res_id, bool) or res_id <= 0:
                continue
            if vals.get("display_type") not in (None, False, "product"):
                continue
            if vals.get("tax_line_id") or vals.get("tax_repartition_line_id"):
                continue
            candidates.append(vals)

        if not candidates:
            return []

        moves = self.env["account.move"].browse(
            {vals["move_id"] for vals in candidates if vals.get("move_id")}
        )
        invoice_ids = set(moves.filtered(lambda move: move.is_invoice()).ids)
        accounts = self.env["account.account"].browse(
            {vals["account_id"] for vals in candidates if vals.get("account_id")}
        )
        counterpart_ids = set(
            accounts.filtered(
                lambda account: account.account_type
                in ("asset_receivable", "liability_payable")
            ).ids
        )
        return [
            vals
            for vals in candidates
            if vals.get("move_id") in invoice_ids
            and vals.get("account_id") not in counterpart_ids
        ]

    @api.model
    def _get_primary_entities_from_billable_items(self, references, source_fields):
        """Resolve each source model in bulk, respecting access and company rules."""
        result = {}
        for model_name, res_ids in references.items():
            paths = source_fields[model_name]
            try:
                records = (
                    self.env[model_name]
                    .with_context(active_test=False)
                    .search_fetch(
                        [("id", "in", sorted(res_ids))],
                        list(dict.fromkeys(path.split(".")[0] for path in paths)),
                    )
                )
                # Prime every relational path on the entire recordset, including
                # fallback paths. Per-record resolution below then uses the cache.
                for path in paths:
                    records.mapped(path)
                entities = {}
                for record in records:
                    partners = (record.mapped(path) for path in paths)
                    partner = next((value for value in partners if value), False)
                    if partner and len(partner) == 1:
                        entities[(model_name, record.id)] = partner.id
                result.update(entities)
            except (AccessError, MissingError):
                # Optional enrichment must not prevent normal invoice creation.
                # Do not use sudo or guess from non-relational invoice data.
                _logger.debug(
                    "Could not resolve invoice primary entities from %s", model_name
                )
        return result

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(vals) for vals in vals_list]
        source_fields = self._get_primary_entity_source_fields()
        candidates = self._get_primary_entity_invoice_values(vals_list, source_fields)
        references = defaultdict(set)
        for vals in candidates:
            references[vals["billable_item_model"]].add(vals["billable_item_res_id"])
        entities = self._get_primary_entities_from_billable_items(
            references, source_fields
        )
        for vals in candidates:
            key = (vals["billable_item_model"], vals["billable_item_res_id"])
            if key in entities:
                vals["primary_entity_id"] = entities[key]
        return super().create(vals_list)

    def write(self, vals):
        if "primary_entity_id" in vals:
            value = vals["primary_entity_id"]
            new_id = value.id if hasattr(value, "id") else value or False
            source_models = self._get_primary_entity_source_fields()
            for line in self:
                if new_id == (line.primary_entity_id.id or False):
                    continue
                # A source and an entity may arrive in the same write call.
                new_source_model = vals.get(
                    "billable_item_model", line.billable_item_model
                )
                new_source_id = vals.get(
                    "billable_item_res_id", line.billable_item_res_id
                )
                if not line.primary_entity_manual_allowed or (
                    new_source_model in source_models and new_source_id
                ):
                    raise UserError(
                        self.env._(
                            "The primary entity cannot be changed on this "
                            "journal item."
                        )
                    )
        return super().write(vals)
