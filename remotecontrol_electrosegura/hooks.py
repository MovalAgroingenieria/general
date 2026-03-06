# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


def uninstall_hook(cr, registry):
    """Deactivate remotecontrol on module uninstall."""
    cr.execute("""
        UPDATE remotecontrol
        SET active = FALSE
        WHERE is_electrosegura = TRUE
    """)
