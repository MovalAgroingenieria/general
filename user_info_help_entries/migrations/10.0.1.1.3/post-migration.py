# -*- coding: utf-8 -*-

def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    # List the external IDs of the records you want to remove.
    record_external_ids = [
        'user_info_help_entries.help_entry_2',
    ]

    for ext_id in record_external_ids:
        try:
            record = env.ref(ext_id)
            record.write({
                'name': 'Foro Novedades',
                'url': 'https://odoo.moval.es/forum/novedades-moval-regadio-3'
            })
        except ValueError:
            # Optionally log that the record was not found
            pass
