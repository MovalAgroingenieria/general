# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from lxml import etree
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    file_ids = fields.One2many(
        string="Associated Files",
        comodel_name="res.file.partnerlink",
        inverse_name="partner_id",
    )

    number_of_files = fields.Integer(
        string="Num. of files",
        compute="_compute_number_of_files",
    )

    attachment_count = fields.Integer(
        string="Files",
        compute="_compute_attachment_count",
        store=False,
    )

    def _compute_attachment_count(self):
        attachment_obj = self.env["ir.attachment"].sudo()
        # batch-friendly: count per res_id in one read_group
        counts = {}
        if self.ids:
            data = attachment_obj.read_group(
                domain=[
                    ("res_model", "=", "res.partner"),
                    ("res_id", "in", self.ids),
                    ("type", "!=", "url"),
                ],
                fields=["res_id"],
                groupby=["res_id"],
            )
            counts = {d["res_id"]: d["res_id_count"] for d in data}
        for partner in self:
            partner.attachment_count = counts.get(partner.id, 0)

    def action_open_partner_files(self):
        self.ensure_one()
        return {
            "name": self.env._("Files"),
            "type": "ir.actions.act_window",
            "res_model": "ir.attachment",
            "view_mode": "kanban,tree,form",
            "domain": [("res_model", "=", "res.partner"), ("res_id", "=", self.id)],
            "context": {
                "default_res_model": "res.partner",
                "default_res_id": self.id,
                "search_default_my_attachments": 0,
            },
            "target": "current",
        }

    # -------------------------
    # Computes
    # -------------------------
    def _compute_number_of_files(self):
        """Count related file links only if the user has filemgmt access."""

        data = self.env["res.file.partnerlink"].read_group(
            domain=[("partner_id", "in", self.ids)],
            fields=["partner_id"],
            groupby=["partner_id"],
        )
        counts = {}
        for d in data:
            # read_group returns partner_id as (id, display_name) or just id
            raw = d.get("partner_id")
            pid = raw[0] if isinstance(raw, (list, tuple)) else raw
            # count key is usually "__count"; keep a fallback
            cnt = d.get("__count", d.get("partner_id_count", 0))
            counts[pid] = cnt

        for rec in self:
            rec.number_of_files = counts.get(rec.id, 0)

    # -------------------------
    # Actions
    # -------------------------
    def action_get_files(self):
        """Open partner's file links in a list view."""
        self.ensure_one()
        if not self.file_ids:
            return False

        tree = self.env.ref(
            "crm_filemgmt.res_file_partnerlink_of_partner_view_tree",
            raise_if_not_found=False,
        )
        search = self.env.ref(
            "crm_filemgmt.res_file_partnerlink_view_search",
            raise_if_not_found=False,
        )

        return {
            "type": "ir.actions.act_window",
            "name": self.env._("File Partnerlinks"),
            "res_model": "res.file.partnerlink",
            "views": ([(tree.id, "tree")] if tree else [(False, "tree")]),
            "view_mode": "tree",
            "search_view_id": (search.id if search else False),
            "target": "current",
            "domain": [("id", "in", self.file_ids.ids)],
            "context": {"search_default_partner_id": self.id},
        }

    # -------------------------
    # View tweaks
    # -------------------------
    def get_view(self, view_id=None, view_type="form", **options):
        """Hide the 'action_get_files' button in form views when user lacks access.

        Replaces deprecated fields_view_get method.
        """
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type != "form":
            return res

        # Parse and modify XML safely
        doc = etree.XML(res["arch"])
        for node in doc.xpath("//button[@name='action_get_files']"):
            # Merge existing modifiers if any; simplest is to force invisibility
            node.set("modifiers", '{"invisible": true}')
        res["arch"] = etree.tostring(doc, encoding="unicode")
        return res
