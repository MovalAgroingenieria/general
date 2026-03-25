# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""GET ``/assembly/attendance`` — managers only; asamblea ``open`` / ``in_session``; localización por ids."""

from odoo import http
from odoo.http import request

_ALLOWED_ASSEMBLY_STATES = frozenset(("open", "in_session"))
_MANAGER_GROUP_XMLID = "base_assembly.assembly_group_manager"


def _attendance_error(status_code, message):
    return request.make_response(
        message,
        status=status_code,
        headers=[
            ("Content-Type", "text/plain; charset=utf-8"),
            ("X-Content-Type-Options", "nosniff"),
            ("Cache-Control", "no-store, private"),
        ],
    )


def _parse_assembly_and_participant_ids(assembly_id, participant_id):
    """``(assembly_id, participant_id)`` como enteros positivos, o ``None``."""
    if assembly_id is None or participant_id is None:
        return None
    str_a, str_p = str(assembly_id).strip(), str(participant_id).strip()
    if not str_a or not str_p:
        return None
    try:
        aid = int(str_a)
        pid = int(str_p)
    except ValueError:
        return None
    if aid <= 0 or pid <= 0:
        return None
    return aid, pid


class AttendanceController(http.Controller):
    @http.route(
        "/assembly/attendance",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def open_attendance(self, assembly_id=None, participant_id=None):
        env = request.env
        parsed = _parse_assembly_and_participant_ids(assembly_id, participant_id)
        if parsed is None:
            return _attendance_error(
                400,
                env._(
                    "Missing or invalid assembly_id or participant_id. "
                    "Both must be positive integers."
                ),
            )
        aid, participant_id_int = parsed

        if not env.user.has_group(_MANAGER_GROUP_XMLID):
            return _attendance_error(
                403,
                env._(
                    "You must belong to the Assembly manager group to open this link."
                ),
            )

        msg_assembly_not_open = env._(
            "This link is only valid while the assembly is open for registration "
            "or in session."
        )

        attendee = env["assembly.attendee"].search(
            [
                ("assembly_id", "=", aid),
                ("partner_id", "=", participant_id_int),
            ],
            limit=1,
        )
        if attendee:
            if attendee.assembly_id.assembly_state not in _ALLOWED_ASSEMBLY_STATES:
                return _attendance_error(403, msg_assembly_not_open)
            return request.redirect(
                "/web#model=assembly.attendee&id=%s&view_type=form" % attendee.id
            )

        assembly = env["assembly.assembly"].browse(aid)
        if not assembly.exists():
            return _attendance_error(404, env._("Assembly not found."))
        if assembly.assembly_state not in _ALLOWED_ASSEMBLY_STATES:
            return _attendance_error(403, msg_assembly_not_open)
        return _attendance_error(
            404,
            env._(
                "No attendee is registered for this assembly with the given participant."
            ),
        )
