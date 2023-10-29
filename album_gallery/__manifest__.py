# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Album Gallery',
    'summary': 'Organize photos and videos in albums in your webpages',
    'version': '16.0.1.1.0',
    'category': 'Moval General Addons',
    'website': 'http://www.moval.es',
    'author': 'Moval Agroingeniería',
    'license': 'AGPL-3',
    'application': True,
    'installable': True,
    'price': 10,
    'currency': 'EUR',
    'images': ['static/description/banner.png'],
    'depends': [
        'website',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/album_gallery_menu_views.xml',
        'views/album_gallery_view.xml',
        'views/album_gallery_website_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'album_gallery/static/src/css/lib/lightgallery-bundle.css',
            'album_gallery/static/src/css/custom.css',
            'album_gallery/static/src/js/lib/lightgallery.umd.js'
            'album_gallery/static/src/js/lib/thumbnail/lg-thumbnail.umd.js'
            'album_gallery/static/src/js/lib/video/lg-video.umd.js'
            'album_gallery/static/src/js/lib/share/lg-share.umd.js'
            'album_gallery/static/src/js/lib/fullscreen/lg-fullscreen.umd.js'
            'album_gallery/static/src/js/lib/zoom/lg-zoom.umd.js'
            'album_gallery/static/src/js/lib/autoplay/lg-autoplay.umd.js'
            'album_gallery/static/src/js/album_gallery.js'
        ],
    },
}
