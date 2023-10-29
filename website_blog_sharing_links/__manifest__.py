# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    'name': 'Blogs Add Old Sharing Links Buttons',
    'category': 'Website/Website',
    'version': '16.0.1.0.0',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'website': 'https://moval.es',
    'application': False,
    'installable': True,
    'depends': [
        'website_blog',
    ],
    'data': [
        'views/website_blog_posts_loop.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_blog_sharing_links/static/src/scss/website_blog.scss',
            'website_blog_sharing_links/static/src/js/website_blog.js',
        ],
    },
}
