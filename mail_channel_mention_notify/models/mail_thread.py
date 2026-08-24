from odoo import models, fields
from markupsafe import Markup, escape as html_escape
import re


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def message_post(self, **kwargs):
        channel_ids = kwargs.pop('channel_ids', None)
        message = super().message_post(**kwargs)
        if not message:
            return message
        if not channel_ids:
            channel_ids = self._extract_channel_ids_from_html(message.body)
        if channel_ids and message:
            self._notify_mentioned_channels(message, channel_ids)
        return message

    def _extract_channel_ids_from_html(self, html_body):

        if not html_body:
            return []
        pattern = r'data-oe-model="mail\.channel"[^>]*data-oe-id="(\d+)"'
        matches = re.findall(pattern, html_body)

        if not matches:
            pattern = r'data-oe-id="(\d+)"[^>]*data-oe-model="mail\.channel"'
            matches = re.findall(pattern, html_body)

        channel_ids = [int(ch_id) for ch_id in matches]
        return channel_ids

    def _notify_mentioned_channels(self, message, channel_ids):
        if self._name == 'mail.channel':
            return

        if not channel_ids:
            return

        if isinstance(channel_ids, int):
            channel_ids = [channel_ids]

        try:
            channels = self.env['mail.channel'].browse(channel_ids).exists()
        except Exception:
            return

        if not channels:
            return

        record_url = self._get_channel_notify_reference()
        task_name = self._get_task_name()
        for channel in channels:
            try:
                notify_body = self._build_channel_notify_body(
                    message.body,
                    task_name,
                    record_url
                )
                channel.message_post(
                    body=notify_body,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                    author_id=message.author_id.id if message.author_id else False,
                )
            except Exception:
                continue

    def _get_channel_notify_reference(self):
        if not self:
            return ''

        record = self[0]
        url = f'/web#id={record.id}&model={self._name}&view_type=form'
        return url

    def _get_task_name(self):
        if not self:
            return ''

        record = self[0]

        # Try different name fields
        if hasattr(record, 'name'):
            try:
                return record.name
            except Exception:
                pass

        if hasattr(record, 'subject'):
            try:
                return record.subject
            except Exception:
                pass

        if hasattr(record, 'title'):
            try:
                return record.title
            except Exception:
                pass

        return ''

    def _build_channel_notify_body(self, original_body, task_name, record_url):
        safe_task_name = html_escape(task_name)
        header = Markup(f'<strong>Tarea: {safe_task_name}</strong><br/><br/>')
        cleaned_body = self._remove_channel_links(original_body)
        button = Markup(
            f'<div style="text-align: center; margin-top: 20px;">'
            f'<a href="{html_escape(record_url)}" class="btn btn-sm btn-primary">'
            f'Ver tarea</a>'
            f'</div>'
        )
        return header + cleaned_body + button

    def _remove_channel_links(self, html_body):
        if not html_body:
            return Markup('')
        pattern = r'<a[^>]*data-oe-model="mail\.channel"[^>]*>([^<]*)</a>'
        cleaned = re.sub(pattern, '', html_body)
        pattern2 = r'<a[^>]*data-oe-id="[^"]*"[^>]*data-oe-model="mail\.channel"[^>]*>([^<]*)</a>'
        cleaned = re.sub(pattern2, '', cleaned)
        return Markup(cleaned)

