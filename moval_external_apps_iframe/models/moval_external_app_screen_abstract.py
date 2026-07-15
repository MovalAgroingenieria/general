# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models, fields, api, exceptions, _

_logger = logging.getLogger(__name__)


class MovalExternalAppScreenAbstract(models.AbstractModel):
    _name = "moval.external.app.screen.abstract"
    _description = "Moval: abstract embedded external-app screen"
    _inherit = ["moval.auth.mixin"]

    # Each concrete subclass must override this with its registered app slug.
    APP_SLUG = None

    app_frame = fields.Text(
        string="Application Frame",
        compute="_compute_app_frame")

    @api.multi
    def _compute_app_frame(self):
        html = self._build_iframe(self.APP_SLUG)
        for record in self:
            record.app_frame = html

    @api.model
    def _get_form_view_xmlid(self):
        """Return the full xmlid of the concrete app's full-screen form view.

        Concrete subclasses must override this method.
        """
        raise NotImplementedError(
            "Concrete external-app screens must implement "
            "_get_form_view_xmlid().")

    @api.model
    def _get_app_name(self):
        app = self.env["moval.external.app"].sudo().search(
            [("slug", "=", self.APP_SLUG)], limit=1)
        return app.name or self.APP_SLUG

    @api.model
    def action_open_iframe(self):
        self.check_access_rights("read")
        record = self.search([], limit=1)
        if not record:
            record = self.create({})
        view = self.env.ref(self._get_form_view_xmlid())
        return {
            "type": "ir.actions.act_window",
            "name": self._get_app_name(),
            "res_model": self._name,
            "view_mode": "form",
            "view_id": view.id,
            "res_id": record.id,
            "target": "inline",
        }

    @api.multi
    def action_open_new_tab(self):
        self.check_access_rights("read")
        url = self._get_app_url_with_ticket(self.APP_SLUG)
        if not url:
            raise exceptions.ValidationError(
                _("Could not authenticate against the external application."))
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }
