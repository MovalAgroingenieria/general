# -*- coding: utf-8 -*-

def migrate(cr, version):
    # This migrations script is wrong, it duplicates the record
    cr.execute("""
        UPDATE user_menu_help_entry d
        SET url = %s
        WHERE d.url = %s
          )
    """, (
        'https://kommodo.ai/share/folder/daitFSYNKQvGvAp6fe9E',
        'https://komododecks.com/share/folder/uMpijVYPLT8enJHURmLc',
    ))
