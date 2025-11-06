# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    top_comment = fields.Html()
    bottom_comment = fields.Html()

    def action_insert_comments(self):
        """Renderiza y coloca los comentarios de plantilla en las
        zonas superior e inferior.
        Compatible con Odoo 18. Evita concatenaciones ineficientes y
        respeta el idioma del partner.
        """
        for picking in self:
            # Idioma de render (partner > entorno)
            lang = picking.partner_id.lang or self.env.lang

            top_parts = []
            bottom_parts = []

            # Si no hay plantillas, no hace nada
            for comment in picking.comment_template_ids:
                # Asegura el contexto de idioma durante el render
                rendered = picking.render_comment(comment.with_context(lang=lang)) or ""

                # Posiciona según la plantilla
                if comment.position == "before_lines":
                    top_parts.append(rendered)
                elif comment.position == "after_lines":
                    bottom_parts.append(rendered)

            # Actualiza en bloque (más limpio y eficiente)
            picking.update(
                {
                    "top_comment": "".join(top_parts),
                    "bottom_comment": "".join(bottom_parts),
                }
            )

        return True
