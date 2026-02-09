# Copyright 2014 Guewen Baconnier (Camptocamp SA)
# Copyright 2013-2014 Nicolas Bessi (Camptocamp SA)
# Copyright 2020 NextERP Romania SRL
# Copyright 2021-2022 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import markupsafe
from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval


class CommentTemplate(models.AbstractModel):
    """Mixin to attach and render base.comment.template records on models.

    Any model inheriting from this abstract model will be able to use
    comment templates (headers/footers) in reports based on the configured
    `base.comment.template` records.
    """

    _name = "comment.template"
    _description = "Mixin to use base.comment.template for headers/footers in reports"

    # Name of the field in downstream models that points to the partner.
    # Override this in inheriting models if the partner field is different
    # (e.g. 'customer_id', 'commercial_partner_id', etc.).
    _comment_template_partner_field_name = "partner_id"

    comment_template_ids = fields.Many2many(
        comodel_name="base.comment.template",
        compute="_compute_comment_template_ids",
        compute_sudo=True,
        string="Comment Templates",
        # pylint: disable=protected-access
        domain=lambda self: [("model_ids", "in", self._name)],
        store=True,
        readonly=False,
        help=(
            "Comment templates applicable to this record, based on the "
            "partner, template configuration and domain."
        ),
    )

    # -------------------------------------------------------------------------
    # COMPUTES
    # -------------------------------------------------------------------------

    @api.depends(lambda self: [self._comment_template_partner_field_name])
    def _compute_comment_template_ids(self):
        """Compute applicable comment templates for each record.

        A template is applicable if:
        - It is enabled for the current model.
        - It is global OR explicitly assigned to the record's partner.
        - Its domain (if any) matches the current record.
        """
        template_model = self.env["base.comment.template"].sudo()

        # Pre-filter templates allowed for this model to avoid access issues.
        # pylint: disable=no-search-all,protected-access
        allowed_templates = template_model.search([]).filtered(
            lambda t: self._name in t.model_ids.mapped("model")
        )
        base_domain = [("id", "in", allowed_templates.ids)]

        for record in self:
            # pylint: disable=protected-access
            partner = record[record._comment_template_partner_field_name]
            commands = [(5,)]  # clear existing links

            templates = template_model.search(
                expression.AND(
                    [
                        [
                            "|",
                            ("id", "in", partner.base_comment_template_ids.ids),
                            ("global_template", "=", True),
                        ],
                        base_domain,
                    ]
                )
            )

            for template in templates:
                # template.domain is a domain string, e.g. "[('amount_total', '>', 0)]"
                domain = safe_eval(template.domain or "[]")
                if not domain or record.filtered_domain(domain):
                    commands.append((4, template.id))

            record.comment_template_ids = commands

    # -------------------------------------------------------------------------
    # RENDER
    # -------------------------------------------------------------------------

    def render_comment(  # pylint: disable=unused-argument
        self,
        comment,
        engine=False,
        add_context=None,
        post_process=False,
    ):
        """Render a single comment for this record using the chosen engine.

        :param comment: base.comment.template record to render.
        :param engine: Optional override of the rendering engine. If falsy,
                       the engine defined on the template is used.
        :param add_context: Extra rendering context to pass to the engine.
        :param post_process: Deprecated / unused in Odoo 18, kept only for
                             compatibility with existing callers.
        :return: Markup-safe HTML string with the rendered comment.
        """
        self.ensure_one()
        # pylint: disable=protected-access
        comment_texts = self.env["mail.render.mixin"]._render_template(
            template_src=comment.text,
            model=self._name,
            res_ids=[self.id],
            engine=engine or comment.engine,
            add_context=add_context,
        )
        return markupsafe.Markup(comment_texts[self.id]) or ""
