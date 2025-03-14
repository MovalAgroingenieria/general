# -*- coding: utf-8 -*-

def migrate(cr, version):
    # Change this records name to Tutoriales específicos
    cr.execute("UPDATE user_menu_help_entry SET name='Tutoriales Específicos'"
               "WHERE id=4")
