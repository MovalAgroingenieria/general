# -*- coding: utf-8 -*-
# 2024 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import _
from odoo.exceptions import AccessError
from odoo import models


class Message(models.Model):
    _inherit = 'mail.message'

    def check_access_rule(self, operation):
        """Access rules of mail.message:
        - read: if
            - author_id == pid, uid is the author OR
            - uid is in the recipients (partner_ids) OR
            - uid has been notified (needaction) OR
            - uid is member of a listener channel (channel_ids.partner_ids) OR
            - uid have read access to the related document if model, res_id
            - otherwise: raise
        - create: if
            - no model, no res_id (private message) OR
            - pid in message_follower_ids if model, res_id OR
            - uid can read the parent OR
            - uid have write or create access on the related document if
              model, res_id, OR
            - otherwise: raise
        - write: if
            - author_id == pid, uid is the author, OR
            - uid is in the recipients (partner_ids) OR
            - uid is moderator of the channel and moderation_status is
              pending_moderation OR
            - uid has write or create access on the related document if
              model, res_id and moderation_status is not pending_moderation
            - otherwise: raise
        - unlink: if
            - uid is moderator of the channel and moderation_status is
              pending_moderation OR
            - uid has write or create access on the related document if
              model, res_id and moderation_status is not pending_moderation
            - otherwise: raise

        Specific case: non-employee users see only messages with subtype
        (aka do not see internal logs).
        """
        def _generate_model_record_ids(msg_val, msg_ids):
            """Generate a dict of model and record IDs.

            :param msg_val: Message values dict
            :param msg_ids: List of message IDs
            :return: Dict in the form {'model': set(res_ids), ...}
            """
            model_record_ids = {}
            for msg_id in msg_ids:
                vals = msg_val.get(msg_id, {})
                if vals.get('model') and vals.get('res_id'):
                    model_record_ids.setdefault(
                        vals['model'], set()
                    ).add(vals['res_id'])
            return model_record_ids

        if self.env.is_superuser():
            return

        # Non-employees see only messages with a subtype (not internal logs)
        # UNLESS they are portal_project_users
        if not self.env['res.users'].has_group('base.group_user') and not \
            self.env['res.users'].has_group(
                'project_limited_access.group_portal_project_user'):
            self._cr.execute(
                '''SELECT DISTINCT message.id, message.subtype_id,
                   subtype.internal
                   FROM "%s" AS message
                   LEFT JOIN "mail_message_subtype" AS subtype
                       ON message.subtype_id = subtype.id
                   WHERE message.message_type = %%s AND
                       (message.is_internal IS TRUE
                        OR message.subtype_id IS NULL
                        OR subtype.internal IS TRUE)
                       AND message.id = ANY (%%s)''' % self._table,
                ('comment', self.ids,)
            )
            if self._cr.fetchall():
                raise AccessError(
                    _(
                        'The requested operation cannot be completed due to '
                        'security restrictions. Please contact your system '
                        'administrator.\n\n(Document type: %s, Operation: %s)',
                        self._description, operation
                    ) + ' - ({} {}, {} {})'.format(
                        _('Records:'), self.ids[:6],
                        _('User:'), self._uid
                    )
                )

        # Read mail_message.ids to have their values
        message_values = {message_id: {} for message_id in self.ids}

        self.flush([
            'model', 'res_id', 'author_id', 'parent_id',
            'moderation_status', 'message_type',
            'partner_ids', 'channel_ids'
        ])
        self.env['mail.notification'].flush([
            'mail_message_id', 'res_partner_id'
        ])
        self.env['mail.channel'].flush([
            'channel_message_ids', 'moderator_ids'
        ])
        self.env['mail.channel.partner'].flush([
            'channel_id', 'partner_id'
        ])
        self.env['res.users'].flush([
            'moderation_channel_ids'
        ])

        if operation == 'read':
            self._cr.execute(
                """
                SELECT DISTINCT
                    m.id, m.model, m.res_id, m.author_id, m.parent_id,
                    COALESCE(
                        partner_rel.res_partner_id,
                        needaction_rel.res_partner_id
                    ),
                    channel_partner.channel_id AS channel_id,
                    m.moderation_status,
                    m.message_type AS message_type
                FROM "%s" m
                LEFT JOIN "mail_message_res_partner_rel" partner_rel
                    ON partner_rel.mail_message_id = m.id
                    AND partner_rel.res_partner_id = %%s
                LEFT JOIN "mail_message_res_partner_needaction_rel"
                    needaction_rel
                    ON needaction_rel.mail_message_id = m.id
                    AND needaction_rel.res_partner_id = %%s
                LEFT JOIN "mail_message_mail_channel_rel" channel_rel
                    ON channel_rel.mail_message_id = m.id
                LEFT JOIN "mail_channel" channel
                    ON channel.id = channel_rel.mail_channel_id
                LEFT JOIN "mail_channel_partner" channel_partner
                    ON channel_partner.channel_id = channel.id
                    AND channel_partner.partner_id = %%s
                WHERE m.id = ANY (%%s)
                """ % self._table,
                (
                    self.env.user.partner_id.id,
                    self.env.user.partner_id.id,
                    self.env.user.partner_id.id,
                    self.ids
                )
            )
            for mid, rmod, rid, author_id, parent_id, partner_id, \
                    channel_id, moderation_status, message_type in \
                    self._cr.fetchall():
                message_values[mid] = {
                    'model': rmod,
                    'res_id': rid,
                    'author_id': author_id,
                    'parent_id': parent_id,
                    'moderation_status': moderation_status,
                    'moderator_id': False,
                    'notified': any((
                        message_values[mid].get('notified'),
                        partner_id,
                        channel_id
                    )),
                    'message_type': message_type,
                }
        elif operation == 'write':
            self._cr.execute(
                """
                SELECT DISTINCT
                    m.id, m.model, m.res_id, m.author_id, m.parent_id,
                    m.moderation_status,
                    COALESCE(
                        partner_rel.res_partner_id,
                        needaction_rel.res_partner_id
                    ),
                    channel_partner.channel_id AS channel_id,
                    channel_moderator_rel.res_users_id AS moderator_id,
                    m.message_type AS message_type
                FROM "%s" m
                LEFT JOIN "mail_message_res_partner_rel" partner_rel
                    ON partner_rel.mail_message_id = m.id
                    AND partner_rel.res_partner_id = %%s
                LEFT JOIN "mail_message_res_partner_needaction_rel"
                    needaction_rel
                    ON needaction_rel.mail_message_id = m.id
                    AND needaction_rel.res_partner_id = %%s
                LEFT JOIN "mail_message_mail_channel_rel" channel_rel
                    ON channel_rel.mail_message_id = m.id
                LEFT JOIN "mail_channel" channel
                    ON channel.id = channel_rel.mail_channel_id
                LEFT JOIN "mail_channel_partner" channel_partner
                    ON channel_partner.channel_id = channel.id
                    AND channel_partner.partner_id = %%s
                LEFT JOIN "mail_channel" moderated_channel
                    ON m.moderation_status = 'pending_moderation'
                    AND m.res_id = moderated_channel.id
                LEFT JOIN "mail_channel_moderator_rel" channel_moderator_rel
                    ON channel_moderator_rel.mail_channel_id =
                    moderated_channel.id
                    AND channel_moderator_rel.res_users_id = %%s
                WHERE m.id = ANY (%%s)
                """ % self._table,
                (
                    self.env.user.partner_id.id,
                    self.env.user.partner_id.id,
                    self.env.user.partner_id.id,
                    self.env.user.id,
                    self.ids
                )
            )
            for mid, rmod, rid, author_id, parent_id, moderation_status, \
                    partner_id, channel_id, moderator_id, message_type in \
                    self._cr.fetchall():
                message_values[mid] = {
                    'model': rmod,
                    'res_id': rid,
                    'author_id': author_id,
                    'parent_id': parent_id,
                    'moderation_status': moderation_status,
                    'moderator_id': moderator_id,
                    'notified': any((
                        message_values[mid].get('notified'),
                        partner_id,
                        channel_id
                    )),
                    'message_type': message_type,
                }
        elif operation == 'create':
            self._cr.execute(
                """
                SELECT DISTINCT
                    id, model, res_id, author_id, parent_id,
                    moderation_status, message_type
                FROM "%s"
                WHERE id = ANY (%%s)
                """ % self._table,
                (self.ids,)
            )
            for mid, rmod, rid, author_id, parent_id, \
                    moderation_status, message_type in self._cr.fetchall():
                message_values[mid] = {
                    'model': rmod,
                    'res_id': rid,
                    'author_id': author_id,
                    'parent_id': parent_id,
                    'moderation_status': moderation_status,
                    'moderator_id': False,
                    'message_type': message_type,
                }
        else:  # unlink
            self._cr.execute(
                """
                SELECT DISTINCT
                    m.id, m.model, m.res_id, m.author_id, m.parent_id,
                    m.moderation_status,
                    channel_moderator_rel.res_users_id AS moderator_id,
                    m.message_type AS message_type
                FROM "%s" m
                LEFT JOIN "mail_channel" moderated_channel
                    ON m.moderation_status = 'pending_moderation'
                    AND m.res_id = moderated_channel.id
                LEFT JOIN "mail_channel_moderator_rel" channel_moderator_rel
                    ON channel_moderator_rel.mail_channel_id =
                    moderated_channel.id
                    AND channel_moderator_rel.res_users_id = %%s
                WHERE m.id = ANY (%%s)
                """ % self._table,
                (self.env.user.id, self.ids,)
            )
            for mid, rmod, rid, author_id, parent_id, moderation_status, \
                    moderator_id, message_type in self._cr.fetchall():
                message_values[mid] = {
                    'model': rmod,
                    'res_id': rid,
                    'author_id': author_id,
                    'parent_id': parent_id,
                    'moderation_status': moderation_status,
                    'moderator_id': moderator_id,
                    'message_type': message_type,
                }

        # Author condition (READ, WRITE, CREATE (private))
        author_ids = []
        if operation == 'read':
            author_ids = [
                mid for mid, message in message_values.items()
                if message.get('author_id') == self.env.user.partner_id.id
            ]
        elif operation == 'write':
            author_ids = [
                mid for mid, message in message_values.items()
                if message.get('moderation_status') != 'pending_moderation' and
                message.get('author_id') == self.env.user.partner_id.id
            ]
        elif operation == 'create':
            author_ids = [
                mid for mid, message in message_values.items()
                if not self.is_thread_message(message)
            ]

        # Moderator condition: allow to WRITE, UNLINK if moderator of a
        # pending message
        moderator_ids = []
        if operation in ['write', 'unlink']:
            moderator_ids = [
                mid for mid, message in message_values.items()
                if message.get('moderator_id')
            ]
        messages_to_check = set(self.ids).difference(
            set(author_ids), set(moderator_ids)
        )
        if not messages_to_check:
            return

        # Recipients condition, for read and write (partner_ids)
        # keep on top, useful for systray notifications
        notified_ids = []
        if operation in ['read', 'write']:
            notified_ids = [
                mid for mid, message in message_values.items()
                if message.get('notified')
            ]

        messages_to_check = messages_to_check.difference(set(notified_ids))
        if not messages_to_check:
            return

        # CRUD: Access rights related to the document
        document_related_ids = []
        document_related_candidate_ids = [
            mid for mid, message in message_values.items()
            if (
                message.get('model') and message.get('res_id') and
                message.get('message_type') != 'user_notification' and
                (
                    message.get('moderation_status') != 'pending_moderation' or
                    operation not in ['write', 'unlink']
                )
            )
        ]
        model_record_ids = _generate_model_record_ids(
            message_values, document_related_candidate_ids
        )
        for model, doc_ids in model_record_ids.items():
            DocumentModel = self.env[model]
            if hasattr(DocumentModel, '_get_mail_message_access'):
                check_operation = DocumentModel._get_mail_message_access(
                    doc_ids, operation
                )
            else:
                check_operation = self.env[
                    'mail.thread']._get_mail_message_access(
                    doc_ids, operation, model_name=model
                )
            records = DocumentModel.browse(doc_ids)
            records.check_access_rights(check_operation)
            mids = records.browse(doc_ids)._filter_access_rules(
                check_operation)
            document_related_ids += [
                mid for mid, message in message_values.items()
                if (
                    message.get('model') == model and
                    message.get('res_id') in mids.ids and
                    message.get('message_type') != 'user_notification' and
                    (
                        message.get('moderation_status') !=
                        'pending_moderation' or
                        operation not in ['write', 'unlink']
                    )
                )
            ]

        messages_to_check = messages_to_check.difference(
            set(document_related_ids)
        )
        if not messages_to_check:
            return

        # Parent condition, for create (check for received notifications for
        # the created message parent)
        if operation == 'create':
            parent_ids = [
                message.get('parent_id') for message in message_values.values()
                if message.get('parent_id')
            ]
            self._cr.execute(
                """
                SELECT DISTINCT m.id, partner_rel.res_partner_id,
                    channel_partner.partner_id
                FROM "%s" m
                LEFT JOIN "mail_message_res_partner_rel" partner_rel
                    ON partner_rel.mail_message_id = m.id
                    AND partner_rel.res_partner_id = %%s
                LEFT JOIN "mail_message_mail_channel_rel" channel_rel
                    ON channel_rel.mail_message_id = m.id
                LEFT JOIN "mail_channel" channel
                    ON channel.id = channel_rel.mail_channel_id
                LEFT JOIN "mail_channel_partner" channel_partner
                    ON channel_partner.channel_id = channel.id
                    AND channel_partner.partner_id = %%s
                WHERE m.id = ANY (%%s)
                """ % self._table,
                (
                    self.env.user.partner_id.id,
                    self.env.user.partner_id.id,
                    parent_ids,
                )
            )
            not_parent_ids = [
                mid[0] for mid in self._cr.fetchall()
                if any([mid[1], mid[2]])
            ]
            notified_ids += [
                mid for mid, message in message_values.items()
                if message.get('parent_id') in not_parent_ids
            ]

        messages_to_check = messages_to_check.difference(set(notified_ids))
        if not messages_to_check:
            return

        # Recipients condition for create (message_follower_ids)
        if operation == 'create':
            for doc_model, doc_ids in model_record_ids.items():
                followers = self.env['mail.followers'].sudo().search([
                    ('res_model', '=', doc_model),
                    ('res_id', 'in', list(doc_ids)),
                    ('partner_id', '=', self.env.user.partner_id.id),
                ])
                fol_mids = [follower.res_id for follower in followers]
                notified_ids += [
                    mid for mid, message in message_values.items()
                    if message.get('model') == doc_model and
                    message.get('res_id') in fol_mids and
                    message.get('message_type') != 'user_notification'
                ]

        messages_to_check = messages_to_check.difference(set(notified_ids))
        if not messages_to_check:
            return

        if not self.browse(messages_to_check).exists():
            return
        raise AccessError(
            _(
                'The requested operation cannot be completed due to security '
                'restrictions. Please contact your system administrator.\n\n'
                '(Document type: %s, Operation: %s)',
                self._description, operation
            ) + ' - ({} {}, {} {})'.format(
                _('Records:'), list(messages_to_check)[:6],
                _('User:'), self._uid
            )
        )

    def _get_search_domain_share(self):
        # project user can see messages as normal users too
        if (self.env['res.users'].has_group(
                'project_limited_access.group_portal_project_user')):
            return [(1, '=', 1)]
        else:
            return [
                '&',
                '&',
                ('is_internal', '=', False),
                ('subtype_id', '!=', False),
                ('subtype_id.internal', '=', False),
            ]
