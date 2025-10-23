# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


def migrate(cr, version):
    """Remove old security rules that will be replaced."""
    if not version:
        return

    # Delete old rules that are being replaced
    cr.execute("""
        DELETE FROM ir_rule
        WHERE id IN (
            SELECT res_id FROM ir_model_data
            WHERE module = 'hr_telework_tracking_site_capacity'
            AND name IN (
                'rule_telework_day_user_own',
                'rule_telework_day_user_edit_draft',
                'rule_telework_day_user_edit'
            )
        )
    """)
