# Copyright 2014 Guewen Baconnier (Camptocamp SA)
# Copyright 2013-2014 Nicolas Bessi (Camptocamp SA)
# Copyright 2020 NextERP Romania SRL
# Copyright 2021-2022 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BaseCommentTemplate(models.Model):
    """Reusable comment templates printed on reports."""

    _name = "base.comment.template"
    _description = "Comment Template"
    _order = "sequence,id"

    active = fields.Boolean(default=True)

    position = fields.Selection(
        string="Position on document",
        selection=[("before_lines", "Top"), ("after_lines", "Bottom")],
        required=True,
        default="before_lines",
        help="Select where this comment will be placed on the report.",
    )

    name = fields.Char(
        translate=True,
        required=True,
        help="Name/description of this comment template.",
    )

    text = fields.Html(
        string="Template",
        translate=True,
        required=True,
        sanitize=False,  # Set to True if you want HTML sanitization.
        help="HTML text that will be inserted into reports.",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        ondelete="cascade",
        index=True,
        help=(
            "If set, the comment template will be available only for "
            "the selected company."
        ),
    )

    global_template = fields.Boolean(
        help=(
            "If enabled, this template is available for all partners that "
            "match the model and domain, without being explicitly assigned "
            "on the partner."
        ),
    )

    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="base_comment_template_res_partner_rel",
        column1="base_comment_template_id",
        column2="res_partner_id",
        string="Partner",
        readonly=True,
        help=(
            "If set, the comment template will be available only for "
            "the selected partners."
        ),
    )

    # Comma-separated list of technical model names (e.g. "sale.order,account.move").
    models = fields.Text(
        required=True,
        help="Comma-separated list of technical model names where this template is available.",
    )

    model_ids = fields.Many2many(
        comodel_name="ir.model",
        compute="_compute_model_ids",
        compute_sudo=True,
        help=(
            "Models where this comment template is available. Only models "
            "allowed to use comment templates are shown."
        ),
        search="_search_model_ids",
    )

    domain = fields.Char(
        string="Filter Domain",
        required=True,
        default="[]",
        help=(
            "Domain (in Odoo domain syntax) that records must satisfy for this "
            "template to be applicable."
        ),
    )

    sequence = fields.Integer(
        required=True,
        default=10,
        help="Lower values give the template a higher priority.",
    )

    engine = fields.Selection(
        selection=[
            ("inline_template", "Inline Template"),
            ("qweb", "QWeb"),
            ("qweb_view", "QWeb View"),
        ],
        required=True,
        default="inline_template",
        help="Engine used to render the template.",
    )

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _get_ir_model_items(self, models):
        """Return allowed ir.model records for the given technical model names."""
        return (
            self.env["ir.model"]
            .sudo()
            .search(
                [
                    ("is_comment_template", "=", True),
                    ("model", "!=", "comment.template"),
                    ("model", "in", models),
                ]
            )
        )

    # -------------------------------------------------------------------------
    # COMPUTES & CONSTRAINTS
    # -------------------------------------------------------------------------

    @api.depends("models")
    def _compute_model_ids(self):
        """Compute the ir.model records from the comma-separated 'models' field."""
        for item in self:
            if item.models:
                model_names = [m.strip() for m in item.models.split(",") if m.strip()]
                models = item._get_ir_model_items(model_names)
            else:
                models = self.env["ir.model"].browse()
            item.model_ids = [(6, 0, models.ids)]

    @api.constrains("models")
    def _check_models(self):
        """Ensure that all models exist and are allowed for comment templates."""
        for item in self.filtered("models"):
            model_names = [m.strip() for m in item.models.split(",") if m.strip()]
            res = item._get_ir_model_items(model_names)
            if not res or len(res) != len(model_names):
                raise ValidationError(_("Some model (%s) not found") % item.models)

    # -------------------------------------------------------------------------
    # NAME GET
    # -------------------------------------------------------------------------

    @api.model
    def name_get(self):
        """Return template name with position (and optionally model names)."""
        res = []
        selection_position = dict(self._fields["position"].selection)
        for item in self:
            name = "{} ({})".format(
                item.name,
                selection_position.get(item.position),
            )
            if self.env.context.get("comment_template_model_display"):
                name += " (%s)" % ", ".join(item.model_ids.mapped("name"))
            res.append((item.id, name))
        return res

    # -------------------------------------------------------------------------
    # SEARCH EXTENSION
    # -------------------------------------------------------------------------

    @api.model
    def _search_model_ids(self, operator, value):
        """Custom search for model_ids, avoiding ir.model access right issues.

        `operator` and `value` belong to the search API signature, but we only
        use `value` as a substring filter on the technical model name.
        """
        if not value:
            return []
        # Use sudo to read all templates, then filter logically in Python.
        allowed_items = (
            self.sudo()
            .search([])
            .filtered(lambda x: value in x.model_ids.mapped("model"))
        )
        return [("id", "in", allowed_items.ids)]
