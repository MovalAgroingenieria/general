# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""GET ``/assembly/attendance`` — managers only; assembly ``open`` / ``in_session``.

Default: HTML landing (context + button to backend form). Append ``direct=1`` for an
immediate redirect to the form and ``text/plain`` error bodies (automation / deep-link).

Lookups intersect ``env.companies`` so deep links stay within the session-allowed
companies (in addition to ``ir.rule`` multi-company domains).
"""

from odoo import http
from odoo.http import request
from odoo.osv import expression

_ALLOWED_ASSEMBLY_STATES = frozenset(("open", "in_session"))
_MANAGER_GROUP_XMLID = "base_assembly.assembly_group_manager"
_DEFAULT_TEMPLATE_LANDING_XMLID = "base_assembly.assembly_attendance_landing_page"
_DEFAULT_TEMPLATE_ERROR_XMLID = "base_assembly.assembly_attendance_error_page"


def _wants_direct_redirect(params):
    val = (params or {}).get("direct")
    if val is None:
        return False
    return str(val).strip().lower() in ("1", "true", "yes")


def _attendance_resolve_qweb_template_ref(env, company, company_field, default_xmlid):
    if company:
        view = getattr(company, company_field, False)
        if view:
            return view.id
    ref = env.ref(default_xmlid, raise_if_not_found=False)
    if ref:
        return ref.id
    return default_xmlid


def _attendance_error_plain(status_code, message):
    return request.make_response(
        message,
        status=status_code,
        headers=[
            ("Content-Type", "text/plain; charset=utf-8"),
            ("X-Content-Type-Options", "nosniff"),
            ("Cache-Control", "no-store, private"),
        ],
    )


def _attendance_error_html(status_code, env, error_title, error_message, company=None):
    company = company or env.company
    template_ref = _attendance_resolve_qweb_template_ref(
        env,
        company,
        "assembly_attendance_error_qweb_id",
        _DEFAULT_TEMPLATE_ERROR_XMLID,
    )
    body = (
        env["ir.ui.view"]
        .sudo()
        ._render_template(
            template_ref,
            {
                "page_title": error_title,
                "error_title": error_title,
                "error_message": error_message,
            },
        )
    )
    return request.make_response(
        body,
        status=status_code,
        headers=[
            ("Content-Type", "text/html; charset=utf-8"),
            ("X-Content-Type-Options", "nosniff"),
            ("Cache-Control", "no-store, private"),
        ],
    )


def _assembly_state_label(env, assembly):
    if not assembly or not assembly.exists():
        return ""
    selection = dict(
        env["assembly.assembly"]._fields["assembly_state"]._description_selection(env)
    )
    key = assembly.assembly_state
    return selection.get(key, key or "")


def _attendance_domain_scoped_to_session_companies(base_domain, env):
    """AND ``base_domain`` with allowed session companies (defense beyond ir.rule)."""
    cids = env.companies.ids
    if not cids:
        return base_domain
    return expression.AND([base_domain, [("company_id", "in", cids)]])


def _parse_assembly_and_participant_ids(assembly_id, participant_id):
    """Return IDs as positive ints, or ``None`` when the input is invalid."""
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
        """Manager deep link; ``participant_id`` is the attendee's partner id."""
        env = request.env
        direct = _wants_direct_redirect(request.params or {})

        parsed = _parse_assembly_and_participant_ids(assembly_id, participant_id)
        if parsed is None:
            return self._attendance_invalid_ids_response(env, direct)
        aid, participant_id_int = parsed

        if not env.user.has_group(_MANAGER_GROUP_XMLID):
            return self._attendance_access_denied_response(env, direct)

        attendee = env["assembly.attendee"].search(
            _attendance_domain_scoped_to_session_companies(
                [
                    ("assembly_id", "=", aid),
                    ("partner_id", "=", participant_id_int),
                ],
                env,
            ),
            limit=1,
        )
        if attendee:
            return self._attendance_attendee_response(env, attendee, direct)
        return self._attendance_no_attendee_response(env, aid, direct)

    def _attendance_invalid_ids_response(self, env, direct):
        msg = env._(
            "Missing or invalid assembly_id or participant_id. "
            "Both must be positive integers."
        )
        if direct:
            return _attendance_error_plain(400, msg)
        return _attendance_error_html(400, env, env._("Invalid link"), msg)

    def _attendance_access_denied_response(self, env, direct):
        msg = env._("You must belong to the Assembly manager group to open this link.")
        if direct:
            return _attendance_error_plain(403, msg)
        return _attendance_error_html(403, env, env._("Access denied"), msg)

    def _attendance_state_error_response(self, env, asm, direct):
        msg = env._(
            "This link is only valid while the assembly is open for registration "
            "or in session."
        )
        if direct:
            return _attendance_error_plain(403, msg)
        return _attendance_error_html(
            403,
            env,
            env._("Assembly not available"),
            msg,
            company=asm.company_id,
        )

    def _attendance_attendee_response(self, env, attendee, direct):
        asm = attendee.assembly_id
        if asm.assembly_state not in _ALLOWED_ASSEMBLY_STATES:
            return self._attendance_state_error_response(env, asm, direct)
        form_hash = "/web#model=assembly.attendee&id=%s&view_type=form" % attendee.id
        if direct:
            return request.redirect(form_hash)
        return self._attendance_render_landing(env, attendee, asm, form_hash)

    def _attendance_render_landing(self, env, attendee, asm, form_hash):
        partner = attendee.partner_id
        landing_ref = _attendance_resolve_qweb_template_ref(
            env,
            asm.company_id,
            "assembly_attendance_landing_qweb_id",
            _DEFAULT_TEMPLATE_LANDING_XMLID,
        )
        body = (
            env["ir.ui.view"]
            .sudo()
            ._render_template(
                landing_ref,
                {
                    "page_title": env._("Attendance — %s", asm.display_name),
                    "heading": env._("Attendance check-in"),
                    "label_assembly": env._("Assembly"),
                    "assembly_name": asm.display_name,
                    "label_member": env._("Member"),
                    "participant_name": partner.display_name if partner else "",
                    "label_state": env._("Assembly status"),
                    "assembly_state_label": _assembly_state_label(env, asm),
                    "open_form_url": form_hash,
                    "open_form_label": env._("Open attendee registration"),
                    "hint_direct": env._(
                        "Tip: append the query parameter ``direct=1`` "
                        "for an immediate redirect without this page "
                        "(e.g. for bookmarks or automation)."
                    ),
                },
            )
        )
        return request.make_response(
            body,
            status=200,
            headers=[
                ("Content-Type", "text/html; charset=utf-8"),
                ("X-Content-Type-Options", "nosniff"),
                ("Cache-Control", "no-store, private"),
            ],
        )

    def _attendance_no_attendee_response(self, env, aid, direct):
        assembly = env["assembly.assembly"].search(
            _attendance_domain_scoped_to_session_companies([("id", "=", aid)], env),
            limit=1,
        )
        if not assembly:
            msg = env._("Assembly not found.")
            if direct:
                return _attendance_error_plain(404, msg)
            return _attendance_error_html(404, env, env._("Not found"), msg)
        if assembly.assembly_state not in _ALLOWED_ASSEMBLY_STATES:
            return self._attendance_state_error_response(env, assembly, direct)
        msg = env._(
            "No attendee is registered for this assembly with the given participant."
        )
        if direct:
            return _attendance_error_plain(404, msg)
        return _attendance_error_html(
            404, env, env._("Not found"), msg, company=assembly.company_id
        )
