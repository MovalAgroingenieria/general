# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api
import requests
from datetime import datetime
from dateutil import parser


class DocumentPage(models.Model):
    _inherit = 'document.page'

    allowed_portal_user_ids = fields.Many2many(
        comodel_name='res.users',
        string='Visible to',
        relation='document_page_allowed_user_rel',
        column1='document_page_id',
        column2='user_id',
        store=True,
        readonly=False,
        copy=False,
    )

    tldv_meeting_id = fields.Char(
        string="TLDV Meeting ID"
    )

    tldv_meeting_url = fields.Char(
        string="TLDV Meeting URL"
    )

    tldv_meeting_time = fields.Datetime(
        string="TLDV Meeting Time"
    )

    draft_name = fields.Char(
        default="Rev 01",
    )

    @api.onchange('name')
    def _onchange_name(self):
        if self.name:
            self.draft_summary = self.name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            project_id = vals.get('project_id')
            if project_id:
                project = self.env['project.project'].browse(project_id)
                if project.privacy_visibility == 'portal':
                    vals['allowed_portal_user_ids'] = [
                        (6, 0, project.allowed_portal_user_ids.ids)]
        return super().create(vals_list)

    def write(self, vals):
        if 'project_id' in vals or 'allowed_portal_user_ids' not in vals:
            for record in self:
                project = record.project_id
                if vals.get('project_id'):
                    project = self.env['project.project'].browse(
                        vals['project_id'])
                if project and project.privacy_visibility == 'portal':
                    vals['allowed_portal_user_ids'] = [
                        (6, 0, project.allowed_portal_user_ids.ids)]
        return super().write(vals)

    def generate_highlights_html(self, data, url):
        html = []
        categories = {}
        html.append(f"<a href='{url}'>{url}</a>")
        for item in data:
            cat = item.get("category", {}).get("label", "")
            categories.setdefault(cat, []).append(item)
        for cat, items in categories.items():
            if items:
                html.append(f"<section><h4><b>{cat}</b> <br></h4><ul>")
                for item in items:
                    startTime = item.get("startTime", 0)
                    if startTime >= 3600:
                        hours = startTime // 3600
                        remainder = startTime % 3600
                        minutes = remainder // 60
                        seg = remainder % 60
                        time_str = f"{hours:02d}:{minutes:02d}:{seg:02d}"
                    else:
                        minutes = startTime // 60
                        seg = startTime % 60
                        time_str = f"{minutes:02d}:{seg:02d}"
                    meeting_url = url
                    link = f"{meeting_url}?t={startTime}"
                    text = item.get("text", "")
                    html.append(f'<li>{text}<!-- -->&nbsp;'
                                f'<a href="{link}">{time_str}</a></li>')
                html.append("</ul><br> </section>")
        return "\n".join(line.strip() for line in html)

    @api.model
    def cron_retrieve_meetings_data(self):
        default_start_date = self.env["ir.config_parameter"].get_param(
            "project_portal_wiki_tldv.tldv_default_start_date")
        last_meeting = self.env["document.page"].search(
            [("tldv_meeting_id", "!=", False)], order="id desc", limit=1)
        last_meeting_date = last_meeting["create_date"] if last_meeting \
            else None
        last_meeting_date = last_meeting_date.date().isoformat() if \
            last_meeting_date else datetime.strptime(
                default_start_date, '%d-%m-%Y').date()
        api_key = self.env["ir.config_parameter"].get_param(
            "project_portal_wiki_tldv.api_key")
        api_url = self.env["ir.config_parameter"].get_param(
            "project_portal_wiki_tldv.tldv_url")
        default_categ = int(self.env["ir.config_parameter"].get_param(
            "project_portal_wiki_tldv.tldv_default_category_id"))
        default_project = int(self.env["ir.config_parameter"].get_param(
            "project_portal_wiki_tldv.tldv_default_project_id"))
        headers = {
            "x-api-key": api_key
        }
        params = {
            "from": last_meeting_date,
            "limit": 1000
        }
        meetings = []
        try:
            meetings_response = requests.get(
                f"{api_url}v1alpha1/meetings",
                headers=headers, params=params
            )
            meetings = meetings_response.json()
        except Exception:
            return
        results = meetings.get("results", [])
        for item in results:
            exists = self.env["document.page"].search([
                ("tldv_meeting_id", "=", item["id"]), ])
            if not exists:
                try:
                    meeting_id_response = requests.get(
                        f"{api_url}v1alpha1/meetings/{item['id']}",
                        headers=headers
                    )
                    meeting_highlights = requests.get(
                        f"{api_url}v1alpha1/meetings/{item['id']}/highlights",
                        headers=headers
                    )
                    meeting_id_response = meeting_id_response.json()
                    meeting_highlights = meeting_highlights.json()
                    meeting_date = parser.isoparse(
                        meeting_id_response["happenedAt"])
                    meeting_date_str = meeting_date.strftime(
                        '%Y-%m-%d %H:%M:%S')
                    html = self.generate_highlights_html(
                        meeting_highlights["data"],
                        url=meeting_id_response["url"])
                    self.env["document.page"].create({
                        "name": meeting_id_response["name"],
                        "tldv_meeting_id": meeting_id_response["id"],
                        "tldv_meeting_url": meeting_id_response["url"],
                        "draft_name": "Rev 01",
                        "draft_summary": "Retrieve from TLDV",
                        "parent_id": default_categ,
                        "project_id": default_project,
                        "content": html,
                        "approved_date": meeting_date_str,
                    })
                except Exception as e:
                    pass
