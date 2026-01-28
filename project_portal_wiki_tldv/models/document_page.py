# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime
import logging
import requests
from dateutil import parser
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class DocumentPage(models.Model):
    _inherit = 'document.page'

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
        # Fetch all meetings using pagination (API limit is 100 per page)
        results = []
        page = 1
        while True:
            params = {
                "from": last_meeting_date,
                "limit": 100,
                "page": page
            }
            try:
                meetings_response = requests.get(
                    f"{api_url}v1alpha1/meetings",
                    headers=headers, params=params
                )
                if meetings_response.status_code != 200:
                    _logger.error(
                        "TLDV API error: %s - %s",
                        meetings_response.status_code,
                        meetings_response.text
                    )
                    return
                meetings = meetings_response.json()
            except Exception as e:
                _logger.error("TLDV API request failed: %s", str(e))
                return
            page_results = meetings.get("results", [])
            results.extend(page_results)
            # Check if there are more pages
            total_pages = meetings.get("pages", 1)
            if page >= total_pages:
                break
            page += 1
        _logger.info("TLDV: Retrieved %d meetings from API", len(results))
        created_count = 0
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
                    if meeting_id_response.status_code != 200:
                        _logger.warning(
                            "TLDV: Failed to fetch meeting %s: %s",
                            item['id'], meeting_id_response.status_code
                        )
                        continue
                    meeting_id_response = meeting_id_response.json()
                    meeting_highlights = meeting_highlights.json()
                    meeting_date = parser.isoparse(
                        meeting_id_response["happenedAt"])
                    meeting_date_str = meeting_date.strftime(
                        '%Y-%m-%d %H:%M:%S')
                    html = self.generate_highlights_html(
                        meeting_highlights.get("data", []),
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
                    created_count += 1
                    _logger.info(
                        "TLDV: Created wiki page for meeting: %s",
                        meeting_id_response["name"]
                    )
                except Exception as e:
                    _logger.error(
                        "TLDV: Error processing meeting %s: %s",
                        item.get('id', 'unknown'), str(e)
                    )
        _logger.info("TLDV: Import completed. Created %d new wiki pages", created_count)
