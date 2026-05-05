# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    cr.execute(
        """
        UPDATE ir_translation
           SET value = src,
               state = 'translated'
         WHERE lang = 'ca_ES'
           AND type = 'model'
           AND name = 'mail.template,subject'
           AND src LIKE %s
           AND value LIKE %s
        """,
        (
            "${object.subject or (object.record_name and 'Re: %s' "
            "% object.record_name)%",
            "${object.subject o (object.record_name i %",
        ),
    )
    _logger.info(
        'mail_notification_subject_ca_fix: fixed %s Catalan '
        'mail template translation row(s).',
        cr.rowcount,
    )
