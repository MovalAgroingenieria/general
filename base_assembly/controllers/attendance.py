# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request


class AttendanceController(http.Controller):
    @http.route(
        "/assembly/attendance",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def open_attendance(self, assembly_id=None, participant_id=None):
        """Open attendance form from QR: ?assembly_id=&participant_id= (partner id)."""
        if not assembly_id or not participant_id:
            return request.render(
                "web.http_error",
                {
                    "status_code": 400,
                    "status_message": "Missing assembly_id or participant_id",
                },
            )
        try:
            aid = int(assembly_id)
            pid = int(participant_id)
        except (TypeError, ValueError):
            return request.render(
                "web.http_error",
                {
                    "status_code": 400,
                    "status_message": "Invalid assembly_id or participant_id",
                },
            )
        if not request.env.user.has_group("base_assembly.assembly_group_manager"):
            raise AccessError(
                request.env._("You must be an Assembly manager to open from QR.")
            )
        assembly = request.env["assembly.assembly"].browse(aid).exists()
        if not assembly:
            return request.render(
                "web.http_error",
                {"status_code": 404, "status_message": "Assembly not found"},
            )
        if assembly.assembly_state not in ("open", "in_session"):
            return request.render(
                "web.http_error",
                {
                    "status_code": 403,
                    "status_message": "Assembly not open for registration/session",
                },
            )
        attendee = request.env["assembly.attendee"].search(
            [("assembly_id", "=", aid), ("partner_id", "=", pid)],
            limit=1,
        )
        if not attendee:
            return request.render(
                "web.http_error",
                {"status_code": 404, "status_message": "Attendee not found"},
            )
        return request.redirect(
            "/web#model=assembly.attendee&id=%s&view_type=form" % attendee.id
        )
