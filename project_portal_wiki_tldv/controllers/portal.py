# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from collections import OrderedDict
from operator import itemgetter
from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as \
    portal_pager
from odoo.osv.expression import OR
from odoo.tools import groupby as groupbyelem


class CustomerPortalHem(CustomerPortal):

    _items_per_page = 15

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'document_page_count' in counters:
            values['document_page_count'] = \
                request.env['document.page'].search_count(
                    [('type', '=', 'content')])
        return values

    @http.route(['/my/document_pages', '/my/document_pages/page/<int:page>'],
                type='http', auth="user", website=True)
    def portal_my_document_pages(
            self, page=1, sortby=None, filterby=None,
            search=None, search_in='name', groupby=None, **kw):
        values = self._prepare_portal_layout_values()
        document_page_model = request.env['document.page']
        # Sorting
        searchbar_sortings = {
            'name': {'label': _('Title'), 'order': 'name'},
            'content': {'label': _('Content'), 'order': 'name'},
            'parent_id': {'label': _('Category'), 'order': 'parent_id,name'},
            'project_id': {'label': _('Project'), 'order': 'project_id,name'},
        }
        if not sortby:
            sortby = 'name'
        order = searchbar_sortings[sortby]['order']
        # Filters
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
        }
        if not filterby:
            filterby = 'all'
        domain = searchbar_filters.get(
            filterby, searchbar_filters['all'])['domain']
        # Searches
        searchbar_inputs = {
            'name': {'input': 'name', 'label': _('Search in Title')},
            'content': {'input': 'content', 'label': _('Search in Content')},
            'parent_id': {'input': 'parent_id', 'label': _(
                'Search in Categories')},
            'project_id': {'input': 'project_id', 'label': _(
                'Search in Projects')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }
        # Group By Options
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'parent_id': {'input': 'parent_id', 'label': _('Category')},
            'project_id': {'input': 'project_id', 'label': _('Project')},
        }
        if search and search_in:
            search_domain = []
            if search_in in ('name', 'all'):
                search_domain = OR(
                    [search_domain, [('name', 'ilike', search)]])
            if search_in in ('parent_id', 'all'):
                search_domain = OR([search_domain, [
                    ('parent_id.name', 'ilike', search)]])
            if search_in in ('project_id', 'all'):
                search_domain = OR([search_domain, [
                    ('project_id.name', 'ilike', search)]])
            domain += search_domain
        domain.append(('type', '=', 'content'))
        # Determine Group By
        if not groupby:
            groupby = 'none'
        if groupby == 'parent_id':
            order = "parent_id, %s" % order
        if groupby == 'project_id':
            order = "project_id, %s" % order
        # Document Pages Count
        document_page_count = document_page_model.search_count(domain)
        # Pager
        pager = portal_pager(
            url="/my/document_pages",
            url_args={'sortby': sortby, 'filterby': filterby,
                      'search_in': search_in, 'search': search,
                      'groupby': groupby},
            total=document_page_count,
            page=page,
            step=self._items_per_page
        )
        # Fetch Documents
        document_pages = document_page_model.search(
            domain, order=order, limit=self._items_per_page,
            offset=pager['offset'])
        # Grouping Logic
        if groupby == 'parent_id':
            grouped_document_pages = [
                request.env['document.page'].concat(*g) for k, g in
                groupbyelem(document_pages, itemgetter('parent_id'))]
        elif groupby == 'project_id':
            grouped_document_pages = [
                request.env['document.page'].concat(*g) for k, g in
                groupbyelem(document_pages, itemgetter('project_id'))]
        else:
            grouped_document_pages = [document_pages] if document_pages else []
        request.session['my_document_pages_history'] = document_pages.ids[:100]
        values.update({
            'document_pages': grouped_document_pages,
            'page_name': 'document_page',
            'default_url': '/my/document_pages',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(
                sorted(searchbar_filters.items())),
            'filterby': filterby,
            'searchbar_groupby': searchbar_groupby,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'search': search,
            'groupby': groupby,
        })
        return request.render(
            "project_portal_wiki_tldv.portal_my_document_pages", values)

    def _document_page_get_page_view_values(self, document_page, access_token,
                                            **kwargs):
        values = {
            'page_name': 'document_page',
            'document_page': document_page,
        }
        return self._get_page_view_values(document_page, access_token, values,
                                          'my_document_pages_history', False,
                                          **kwargs)

    @http.route(['/my/document_page/<int:document_page_id>'],
                type='http', auth="public", website=True)
    def portal_my_document_page(self, document_page_id=None, access_token=None,
                                **kw):
        try:
            document_page_sudo = self._document_check_access(
                'document.page', document_page_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        values = self._document_page_get_page_view_values(
            document_page_sudo, access_token, **kw)
        return request.render(
            "project_portal_wiki_tldv.portal_my_document_page", values)
