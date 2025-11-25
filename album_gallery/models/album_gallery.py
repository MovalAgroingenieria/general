# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api
import base64
import subprocess
import tempfile
import logging
import os

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    video_attachment_id = fields.Many2one('ir.attachment',
                                          string='Related Video Attachment')

    def create(self, vals):
        result = super(IrAttachment, self).create(vals)
        if result.mimetype.startswith('video/'):
            result.public = True
            if result.mimetype.startswith('video/'):
                video_data = base64.b64decode(result.datas)
                with tempfile.NamedTemporaryFile(
                    suffix=f".{result.mimetype.split('/')[-1]}",
                        delete=False) as video_temp:
                    video_temp.write(video_data)
                    video_path = str(video_temp.name)
                with tempfile.NamedTemporaryFile(
                        suffix='.png', delete=False) as thumbnail_temp:
                    thumbnail_path = thumbnail_temp.name
                subprocess.call(['ffmpeg', '-y', '-loglevel', 'quiet',
                                 '-i', video_path, '-ss', '00:00:01',
                                 '-vframes', '1', thumbnail_path])
                with open(thumbnail_path, 'rb') as f:
                    thumbnail_data = f.read()
                thumbnail_base64 = base64.b64encode(thumbnail_data).decode()
                self.env['ir.attachment'].create({
                    'name': f'Thumbnail for {result.id}',
                    'type': 'binary',
                    'datas': thumbnail_base64,
                    'res_model': 'album.gallery',
                    'mimetype': 'image/png',
                    'public': True,
                    'video_attachment_id': result.id,
                })
                os.remove(video_path)
                os.remove(thumbnail_path)
        return result

    def unlink(self):
        thumbnail_attachments = self.env['ir.attachment'].search([
            ('video_attachment_id', 'in', self.ids)
        ])
        result = super(IrAttachment, self).unlink()
        if thumbnail_attachments:
            thumbnail_attachments.unlink()
        return result


class AlbumGallery(models.Model):
    _name = 'album.gallery'
    _description = "Album Gallery"
    _rec_name = 'name'
    _inherit = 'mail.thread'
    _order = 'sequence asc'

    sequence = fields.Integer(string="Sequence")
    name = fields.Char("Album Name", required=True)
    description = fields.Text("Album Description")
    active = fields.Boolean(
        'Active',
        default=True,
        help="If unchecked, it hides the album")
    website_id = fields.Many2one('website',
                                 string='Website',
                                 default=lambda self:
                                 self._get_default_website())

    def _get_default_website(self):
        default_website = self.env.ref('website.default_website')
        return default_website.id if default_website else False

    @api.model
    def create(self, values):
        if 'sequence' not in values:
            values['sequence'] = 1
            self._reorganize_sequence(2)
        album = super(AlbumGallery, self).create(values)
        return album

    def write(self, values):
        album = super(AlbumGallery, self).write(values)
        return album

    def unlink(self):
        for record in self:
            thumbnails = self.env['ir.attachment'].search([(
                'video_attachment_id', '=', record.id)])
            thumbnails.unlink()
            super(AlbumGallery, record).unlink()
            self._reorganize_sequence(1)

    def _reorganize_sequence(self, func):
        ordered_records = self.search([], order='sequence asc,'
                                                ' create_date desc')
        new_sequence = func
        for record in ordered_records:
            record.sequence = new_sequence
            new_sequence += 1
