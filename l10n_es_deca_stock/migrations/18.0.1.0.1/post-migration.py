# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import SUPERUSER_ID, api


def _find_picking(env, deca):
    """Return the single stock.picking a DECA originated from, or empty.

    ``goods_description`` stores the originating picking reference: either the
    picking ``name`` or its ``origin`` (see ``_prepare_deca_vals``). Matching on
    ``name`` is unique; matching on ``origin`` can return several pickings, so it
    is only accepted when it resolves to exactly one record (optionally narrowed
    by the DECA transport date).
    """
    reference = deca.goods_description
    if not reference:
        return env["stock.picking"]
    picking = env["stock.picking"].search([("name", "=", reference)], limit=2)
    if len(picking) == 1:
        return picking
    domain = [("origin", "=", reference)]
    if deca.transport_date:
        day = str(deca.transport_date)
        domain += [
            ("scheduled_date", ">=", "%s 00:00:00" % day),
            ("scheduled_date", "<=", "%s 23:59:59" % day),
        ]
    picking = env["stock.picking"].search(domain, limit=2)
    if len(picking) == 1:
        return picking
    return env["stock.picking"]


def migrate(cr, version):
    """Backfill picking_id on existing DECA records.

    The ORM creates the ``picking_id`` column when the module is updated. This
    step links already-stored DECA documents to their originating stock picking.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    decas = env["deca.document"].with_context(tracking_disable=True).search(
        [("picking_id", "=", False)]
    )
    for deca in decas:
        picking = _find_picking(env, deca)
        if picking:
            deca.picking_id = picking.id
