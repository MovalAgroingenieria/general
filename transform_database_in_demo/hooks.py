# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


def post_init_hook(cr, registry):

    # Partner names
    query_1 = """
        UPDATE res_partner SET firstname = 'María' WHERE id != 1
            AND is_company = False;
        UPDATE res_partner SET lastname = 'Demo' WHERE id != 1 AND
            is_company = False;
        UPDATE res_partner AS c SET
            name = (SELECT CONCAT_WS(' ', lastname, lastname2, firstname)
            FROM res_partner WHERE c.id = res_partner.id) WHERE id != 1 AND
            is_company = False;
        UPDATE res_partner AS c SET
            display_name =
                (SELECT CONCAT_WS(' ', lastname, lastname2, firstname)
            FROM res_partner WHERE c.id = res_partner.id) WHERE id != 1 AND
            is_company = False;
    """

    # Company names
    query_2 = """
        UPDATE res_partner AS c SET
            lastname = (SELECT CONCAT(substring(name,1,3),
                substring(name,position(',' in name),5)) FROM res_partner
            WHERE is_company = True AND c.id = res_partner.id)
        WHERE is_company = True;
        UPDATE res_partner AS c SET
            display_name = (SELECT CONCAT(substring(name,1,3),
                substring(name,position(',' in name),5)) FROM res_partner
            WHERE is_company = True AND c.id = res_partner.id)
        WHERE is_company = True;
        UPDATE res_partner AS c SET
            name = (SELECT CONCAT(substring(name,1,3),
                substring(name,position(',' in name),5)) FROM res_partner
            WHERE is_company = True AND c.id = res_partner.id)
        WHERE is_company = True;
        UPDATE res_partner SET firstname = 'Demo' WHERE is_company = True
            AND id != 1;
        UPDATE res_company SET name = 'Compania Demo';
    """

    # Phone / Mobile / Email / VAT
    query_3 = """
        UPDATE res_partner SET mobile = '669 93 74 66' WHERE id != 1 OR id != 2;
        UPDATE res_partner SET phone = '868 45 30 90' WHERE id != 1 OR id != 2;
        UPDATE res_partner SET email = 'info@moval.es' WHERE id != 1 OR id != 2;
        UPDATE res_partner SET vat = 'ESA00000000' WHERE id != 1 OR id != 2;
    """

    # Users password and login
    query_4 = """
        UPDATE res_users SET password =
        '$pbkdf2-sha512$25000$vTfGOIfw/l8r5ZzTuleKsQ$QE3I/BI33e7y0hRt7Q.Bs8vJG'
        'HaU05Plu0yGZFNxtD5/0ijwZ33iCscUvzCHs6lu4M5rhMWFgiZrgtdhlePHkg'
        WHERE password IS NOT NULL;
    """

    # @TODO: Users login
#      UPDATE res_users AS c SET login = (SELECT CONCAT(substring(login,1,3),
#             substring(login,position('@' in login),5)) FROM res_users
#         WHERE c.id = res_users.id AND c.id != 1);

    # Delete attachments
#    query_5 = """
#        DELETE FROM ir_attachment WHERE store_fname IS NOT NULL
#            AND store_fname<>'';
#    """

    # Block mail server
    query_6 = """
        DELETE FROM ir_mail_server;
        INSERT INTO ir_mail_server (name, smtp_host, smtp_port,
            smtp_encryption, smtp_user, smtp_pass, active, sequence,
            smtp_authentication, smtp_debug)
        VALUES ('smtp_inactive', 'fake_host', '55555', 'none', 'fake_user',
            'nopassword', True, 10, 'login', False);
    """

    # @TODO: google agenda tokens
#             UPDATE ir_config_parameter SET value=''
#          WHERE key='google_calendar_client_id'
#             OR key='google_calendar_client_secret';

    try:
        cr.savepoint()
        cr.execute(query_1)
        cr.commit()
    except:
        cr.rollback()

    try:
        cr.savepoint()
        cr.execute(query_2)
        cr.commit()
    except:
        cr.rollback()

    try:
        cr.savepoint()
        cr.execute(query_3)
        cr.commit()
    except:
        cr.rollback()

    try:
        cr.savepoint()
        cr.execute(query_4)
        cr.commit()
    except:
        cr.rollback()

#     try:
#         cr.savepoint()
#         cr.execute(query_5)
#         cr.commit()
#     except:
#         cr.rollback()

    try:
        cr.savepoint()
        cr.execute(query_6)
        cr.commit()
    except:
        cr.rollback()
