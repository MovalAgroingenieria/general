# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None,
                   orderby=False, lazy=True):
        groups = super().read_group(domain, fields, groupby,
                                    offset=offset, limit=limit,
                                    orderby=orderby, lazy=lazy)
        if 'type_id' in groupby and groups:
            type_ids = [
                g['type_id'][0] for g in groups
                if g.get('type_id') and g['type_id']
            ]
            types = self.env['project.type'].browse(type_ids)
            seq_map = {t.id: t.sequence for t in types}
            groups = sorted(
                groups,
                key=lambda g: (
                    seq_map.get(g['type_id'][0], 0)
                    if g.get('type_id') and g['type_id'] else 0
                )
            )
        return groups
