# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    cr.execute("""
        SELECT id, cmr_tractor_license_plate, cmr_semi_trailer_license_plate
        FROM stock_picking
        WHERE (cmr_tractor_license_plate IS NOT NULL
               AND TRIM(cmr_tractor_license_plate) <> '')
           OR (cmr_semi_trailer_license_plate IS NOT NULL
               AND TRIM(cmr_semi_trailer_license_plate) <> '')
    """)
    rows = cr.fetchall()
    if not rows:
        return

    plate_cache = {}

    def get_or_create(plate):
        if not plate:
            return None
        key = plate.strip()
        if not key:
            return None
        if key in plate_cache:
            return plate_cache[key]
        cr.execute(
            "SELECT id FROM cmr_license_plate WHERE name = %s LIMIT 1",
            (key,),
        )
        existing = cr.fetchone()
        if existing:
            plate_cache[key] = existing[0]
            return existing[0]
        cr.execute(
            "INSERT INTO cmr_license_plate "
            "(name, active, create_date, write_date) "
            "VALUES (%s, true, NOW() AT TIME ZONE 'UTC', "
            "NOW() AT TIME ZONE 'UTC') RETURNING id",
            (key,),
        )
        new_id = cr.fetchone()[0]
        plate_cache[key] = new_id
        return new_id

    for picking_id, tractor_plate, trailer_plate in rows:
        tractor_id = get_or_create(tractor_plate)
        trailer_id = get_or_create(trailer_plate)
        cr.execute(
            "UPDATE stock_picking "
            "SET cmr_tractor_license_plate_id = %s, "
            "    cmr_semi_trailer_license_plate_id = %s "
            "WHERE id = %s",
            (tractor_id, trailer_id, picking_id),
        )

    _logger.info(
        "stock_picking_cmr_license_plate: imported %s license plates "
        "from %s pickings.",
        len(plate_cache),
        len(rows),
    )
