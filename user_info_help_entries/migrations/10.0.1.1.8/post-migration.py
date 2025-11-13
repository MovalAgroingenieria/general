# -*- coding: utf-8 -*-

def migrate(cr, version):
    # Fix URL update that failed in version 10.0.1.1.7 due to SQL syntax error
    cr.execute("""
        UPDATE user_menu_help_entry
        SET url = %s
        WHERE url = %s
    """, (
        'https://kommodo.ai/share/folder/daitFSYNKQvGvAp6fe9E',
        'https://komododecks.com/share/folder/uMpijVYPLT8enJHURmLc',
    ))