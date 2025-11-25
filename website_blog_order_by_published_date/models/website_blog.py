# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class BlogPost(models.Model):
    _inherit = "blog.post"
    _order = 'published_date DESC'
