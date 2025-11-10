# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models

# pylint: disable=protected-access


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    @api.model
    def get_paperformat(self):
        # pylint: disable=except-pass
        """
        Return the paperformat to use for this report,
         allowing an explicit context override.

        Supported context keys:
          - paperformat_id: integer ID of report.paperformat
          - paperformat_xmlid: external id string like "module.paperformat_name"
        """
        paperformat = super().get_paperformat()
        ctx = self.env.context

        # 1) Override by numeric ID
        pf_id = ctx.get("paperformat_id")
        if pf_id:
            pf = self.env["report.paperformat"].browse(int(pf_id)).exists()
            if pf:
                return pf

        # 2) Override by XMLID (optional convenience for callers)
        xmlid = ctx.get("paperformat_xmlid")
        if xmlid:
            try:
                pf = self.env.ref(xmlid)
                if pf and pf._name == "report.paperformat":
                    return pf
            except ValueError:
                # invalid or missing xmlid -> ignore and fall back
                pass

        # 3) Default behavior (company/report-defined paperformat)
        return paperformat
