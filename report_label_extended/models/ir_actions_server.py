# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    label_template = fields.Char(
        help=(
            "Logical XMLID (module.name) of the QWeb template used for label "
            "printing. This is used by the 'Open associated label view' action."
        ),
    )

    def report_label_associated_view(self):
        """Open (QWeb) views associated with the template in label_template.

        Returns an ir.actions.act_window dict opening ir.ui.view filtered by:
        - type = 'qweb'
        - name ilike the template name part
        - OR key = full logical XMLID (module.name)
        """
        self.ensure_one()

        # 1) Get the "Views" window action. Use a fallback if the XMLID is missing.
        try:
            # pylint: disable=protected-access
            res = self.env["ir.actions.act_window"]._for_xml_id("base.action_ui_view")
        except Exception:  # pylint: disable=broad-exception-caught
            # Fallback: search any act_window that opens ir.ui.view.
            action = self.env["ir.actions.act_window"].search(
                [("res_model", "=", "ir.ui.view")], limit=1
            )
            if not action:
                return False
            res = action.read()[0]

        # 2) Only proceed when label_template has the "module.name" format.
        label = (self.label_template or "").strip()
        if "." not in label:
            return False

        # Split once to avoid breaking names that could contain extra dots.
        _module, name = label.split(".", 1)

        # 3) Filter QWeb views by approximate name or exact key (XMLID).
        res["domain"] = [
            ("type", "=", "qweb"),
            "|",
            ("name", "ilike", name),
            ("key", "=", label),
        ]

        # Ensure we open in list+form in case the base action differs.
        res.setdefault("view_mode", "list,form")

        return res
