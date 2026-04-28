# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import http
from odoo.http import request


class CimComplaintsChannelWebsiteController(http.Controller):

    @http.route('/page/complaints-channel', type='http', auth='public',
                website=True)
    def complaints_channel_page(self, **kwargs):
        website_company = request.website.company_id
        legal_data = request.env[
            'cim.complaints.channel.website'].sudo().search(
            [('company_id', '=', website_company.id)],
            limit=1)
        if not legal_data:
            legal_data = request.env[
                'cim.complaints.channel.website'].sudo().search(
                [('active', '=', True)],
                limit=1)
        if legal_data and legal_data.company_id:
            website_company = legal_data.company_id
        return request.render(
            'cim_complaints_channel_website.complaints_channel_page',
            {
                'legal_data': legal_data,
                'website_company': website_company,
            })

    @http.route('/page/new-complaint', type='http', auth='public',
                website=True)
    def new_complaint_page(self, **kwargs):
        return request.render(
            'cim_complaints_channel_website.new_complaint_page', {})

    @http.route('/page/new-communication', type='http', auth='public',
                website=True)
    def new_communication_page(self, **kwargs):
        return request.render(
            'cim_complaints_channel_website.new_communication_page', {})

    @http.route('/page/info-complaints-channel', type='http', auth='public',
                website=True)
    def info_complaints_channel_page(self, **kwargs):
        website_company = request.website.company_id
        return request.render(
            'cim_complaints_channel_website.info_complaints_channel_page',
            {
                'website_company': website_company,
            })
