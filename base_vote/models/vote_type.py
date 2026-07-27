# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from jinja2.sandbox import SandboxedEnvironment
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class VoteType(models.Model):
    _name = "vote.type"
    _description = "Vote Type"
    _order = "name"

    _sql_constraints = [
        ("code_uniq", "UNIQUE(code)", "The code must be unique."),
    ]

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    description = fields.Text(translate=True)
    formula = fields.Text(
        help=(
            "Jinja2 formula. Variable: partner (contact). Must return a number. "
            "TER parcels on partner.parcel_ids use numeric field area_official (ha); "
            "totals: partner.area_official_parcels."
        ),
    )
    vote_value_type = fields.Selection(
        [("integer", "Integer"), ("float", "Decimal")],
        string="Result type",
        default="integer",
        required=True,
    )
    decimal_precision = fields.Integer(
        string="Decimal places",
        default=2,
        help="Only used when result type is Decimal.",
    )
    partner_domain = fields.Text(
        string="Partner domain",
        default="[]",
        help="Domain to filter which partners this vote type applies to.",
    )
    partner_vote_ids = fields.One2many(
        "partner.vote",
        "vote_type_id",
        string="Partner votes",
    )
    active = fields.Boolean(default=True)
    last_compute_date = fields.Datetime(string="Last computed", readonly=True)
    last_compute_log = fields.Text(string="Last compute log", readonly=True)
    partner_vote_count = fields.Integer(
        string="Partner votes count",
        compute="_compute_partner_vote_count",
        store=False,
    )

    def _get_effective_formula(self):
        """Return the Jinja2 expression to evaluate."""
        self.ensure_one()
        return (self.formula or "").strip()

    @api.depends("partner_vote_ids")
    def _compute_partner_vote_count(self):
        for record in self:
            record.partner_vote_count = len(record.partner_vote_ids)

    def evaluate_formula(self, partner):
        """Evaluate formula for one partner.

        Returns (value, detail_str) or (0, error).
        """
        self.ensure_one()
        expr = self._get_effective_formula()
        if not expr:
            return 0.0, ""
        try:
            env = SandboxedEnvironment()
            if not expr.startswith("{{"):
                expr = "{{ %s }}" % expr
            template = env.from_string(expr)
            result = template.render(partner=partner)
            if result is None or result == "":
                return 0.0, str(result)
            num = float(result)
            if self.vote_value_type == "integer":
                num = int(num)
            else:
                num = round(num, self.decimal_precision)
            detail = self.env._(
                "Formula: %(formula)s\nResult: %(result)s",
                formula=expr,
                result=num,
            )
            return num, detail
        except Exception as e:  # pylint: disable=broad-exception-caught
            _logger.warning(
                "base_vote: formula error for partner %s type %s: %s",
                partner.id,
                self.code,
                e,
            )
            return 0.0, f"Error: {e}"

    def test_formula(self, formula, partner_id):
        """Evaluate a formula string for a given partner (for the "Test" button).

        Returns a dict: {'value': number, 'detail': str} on success, or {'error': str}.
        """
        self.ensure_one()
        partner = self.env["res.partner"].browse(partner_id)
        if not partner.exists():
            return {"error": self.env._("Partner not found.")}
        formula = (formula or "").strip()
        if not formula:
            return {"error": self.env._("Formula is empty.")}
        try:
            env = SandboxedEnvironment()
            if not formula.startswith("{{"):
                formula = "{{ %s }}" % formula
            template = env.from_string(formula)
            result = template.render(partner=partner)
            if result is None or result == "":
                return {"value": 0, "detail": self.env._("Result: empty")}
            num = float(result)
            if self.vote_value_type == "integer":
                num = int(num)
            else:
                num = round(num, self.decimal_precision)
            return {
                "value": num,
                "detail": self.env._("Result: %(result)s", result=num),
            }
        except Exception as e:  # pylint: disable=broad-exception-caught
            return {"error": str(e)}

    def _get_partners_to_compute(self):
        """Partners matching partner_domain."""
        self.ensure_one()
        try:
            domain = safe_eval(self.partner_domain or "[]", {"__builtins__": {}})
        except (TypeError, ValueError, SyntaxError, MemoryError):
            domain = []
        return self.env["res.partner"].search(domain)

    def action_recompute_votes(self):
        """Recompute votes for all partners matching domain."""
        self.ensure_one()
        if not self.active:
            raise UserError(self.env._("Cannot recompute an archived vote type."))
        partners = self._get_partners_to_compute()
        partner_vote_model = self.env["partner.vote"]
        if partners:
            # oca-review: full stale cleanup for this vote type before recompute.
            stale_votes = partner_vote_model.search(
                [
                    ("vote_type_id", "=", self.id),
                    ("partner_id", "not in", partners.ids),
                ]
            )
        else:
            # oca-review: empty domain means all vote lines for this type become stale.
            stale_votes = partner_vote_model.search([("vote_type_id", "=", self.id)])
        stale_votes.unlink()
        log_lines = []
        for partner in partners:
            value, detail = self.evaluate_formula(partner)
            if "Error:" in detail:
                log_lines.append(
                    self.env._(
                        "Partner %(pid)s (%(name)s): %(detail)s",
                        pid=partner.id,
                        name=partner.display_name,
                        detail=detail,
                    ),
                )
            vote = partner_vote_model.search(
                [
                    ("partner_id", "=", partner.id),
                    ("vote_type_id", "=", self.id),
                ],
                limit=1,
            )
            now = fields.Datetime.now()
            if self.vote_value_type == "integer":
                vals = {
                    "vote_count_integer": int(value),
                    "vote_count_float": 0.0,
                    "last_compute_date": now,
                    "formula_detail": detail,
                }
            else:
                vals = {
                    "vote_count_integer": 0,
                    "vote_count_float": value,
                    "last_compute_date": now,
                    "formula_detail": detail,
                }
            if vote:
                vote.write(vals)
            else:
                partner_vote_model.create(
                    {
                        "partner_id": partner.id,
                        "vote_type_id": self.id,
                        **vals,
                    },
                )
        summary = self.env._("%(count)s partners processed.", count=len(partners))
        if log_lines:
            summary += "\n\n" + "\n".join(log_lines)
        else:
            summary += " " + self.env._("No errors.")
        self.write(
            {
                "last_compute_date": fields.Datetime.now(),
                "last_compute_log": summary,
            },
        )
        return True

    @api.model
    def _recompute_all_active_vote_types(self):
        """Called by cron to recompute all active vote types."""
        for vote_type in self.search([("active", "=", True)]):
            try:
                vote_type.action_recompute_votes()
            except Exception as e:  # pylint: disable=broad-exception-caught
                _logger.exception(
                    "base_vote cron: recompute %s failed: %s",
                    vote_type.code,
                    e,
                )
