# 2022 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import re
import requests
import io
import base64
import subprocess
from PIL import Image
from pyproj import Proj, transform
from odoo import models, fields, api, _


class SimplegisModel(models.AbstractModel):
    _name = 'simplegis.model'
    _description = 'Simple-GIS Model'

    # Linked GIS table ("wua_gis_parcel", for example).
    _gis_table = ''

    # "geom" field.
    _geom_field = 'geom'

    # Field for link.
    _link_field = 'name'

    # Template for the URL of Google Maps based on coordinates.
    _url_googlemaps = 'https://maps.google.com/maps?' + \
        't=h&q=loc:ycval+xcval'

    # Default size for WMS images.
    NORMAL_SIZE = 384

    geom_ewkt = fields.Char(
        string='EWKT Geometry',
        compute='_compute_geom_ewkt')

    simplified_geom_ewkt = fields.Char(
        string='EWKT Geometry based on integer values',
        compute='_compute_simplified_geom_ewkt')

    oriented_envelope_ewkt = fields.Char(
        string='EWKT Geometry for oriented envelope',
        compute='_compute_oriented_envelope_ewkt')

    area_gis = fields.Integer(
        string='GIS Area (m²)',
        compute='_compute_area_gis')

    area_gis_ha = fields.Float(
        string='GIS Area (ha)',
        digits=(32, 2),
        compute='_compute_area_gis_ha')

    centroid_ewkt = fields.Char(
        string='EWKT Centroid',
        compute='_compute_centroid_ewkt')

    simplified_centroid_ewkt = fields.Char(
        string='EWKT Centroid based on integer values',
        compute='_compute_simplified_centroid_ewkt')

    with_gis_link = fields.Boolean(
        string='With GIS link',
        compute='_compute_with_gis_link',
        search='_search_with_gis_link',)

    googlemaps_link = fields.Char(
        string='Google Maps Link',
        default='',
        compute='_compute_googlemaps_link',)

    def _compute_geom_ewkt(self):
        geom_ok = self._geom_ok()
        for record in self:
            geom_ewkt = ''
            if geom_ok:
                self.env.cr.execute("""
                    SELECT postgis.st_asewkt(""" + self._geom_field + """)
                    FROM """ + self._gis_table + """
                    WHERE """ + self._link_field + """='""" + record.name + """'""")
                query_results = self.env.cr.dictfetchall()
                if (query_results and
                   query_results[0].get('st_asewkt') is not None):
                    geom_ewkt = query_results[0].get('st_asewkt')
            record.geom_ewkt = geom_ewkt

    def _compute_simplified_geom_ewkt(self):
        for record in self:
            simplified_geom_ewkt = ''
            geom_ewkt = record.geom_ewkt
            if geom_ewkt:
                simplified_geom_ewkt = \
                    re.sub(r'\d+\.\d{1,}', lambda m: str(
                        int(round(float(m.group(0))))), geom_ewkt)
            record.simplified_geom_ewkt = simplified_geom_ewkt

    def _compute_oriented_envelope_ewkt(self):
        geom_ok = self._geom_ok()
        for record in self:
            oriented_envelope_ewkt = ''
            if geom_ok:
                self.env.cr.execute("""
                    SELECT postgis.st_asewkt(postgis.st_orientedenvelope(""" + self._geom_field + """))
                    FROM """ + self._gis_table + """
                    WHERE """ + self._link_field + """='""" + record.name + """'""")
                query_results = self.env.cr.dictfetchall()
                if (query_results and
                   query_results[0].get('st_asewkt') is not None):
                    oriented_envelope_ewkt = query_results[0].get('st_asewkt')
            record.oriented_envelope_ewkt = oriented_envelope_ewkt

    def _compute_area_gis(self):
        geom_ok = self._geom_ok()
        for record in self:
            area_gis = 0
            if geom_ok:
                self.env.cr.execute("""
                    SELECT postgis.geometrytype(""" + self._geom_field + """),
                    postgis.st_area(""" + self._geom_field + """)
                    FROM """ + self._gis_table + """
                    WHERE """ + self._link_field + """
                    ='""" + record.name + """'""")
                query_results = self.env.cr.dictfetchall()
                if (query_results and
                   query_results[0].get('geometrytype') is not None):
                    geometry_type = \
                        query_results[0].get('geometrytype').lower()
                    if (geometry_type == 'polygon' or
                       geometry_type == 'multipolygon'):
                        area_gis = \
                            round(float(query_results[0].get('st_area')))
            record.area_gis = area_gis

    def _compute_area_gis_ha(self):
        for record in self:
            record.area_gis_ha = record.area_gis / 10000

    def _compute_centroid_ewkt(self):
        geom_ok = self._geom_ok()
        for record in self:
            centroid_ewkt = ''
            if geom_ok:
                self.env.cr.execute("""
                    SELECT postgis.st_asewkt
                    (st_centroid(""" + self._geom_field + """))
                    FROM """ + self._gis_table + """
                    WHERE """ + self._link_field + """='""" + record.name + """'""")
                query_results = self.env.cr.dictfetchall()
                if (query_results and
                   query_results[0].get('st_asewkt') is not None):
                    centroid_ewkt = query_results[0].get('st_asewkt')
            record.centroid_ewkt = centroid_ewkt

    def _compute_simplified_centroid_ewkt(self):
        for record in self:
            simplified_centroid_ewkt = ''
            centroid_ewkt = record.centroid_ewkt
            if centroid_ewkt:
                simplified_centroid_ewkt = \
                    re.sub(r'\d+\.\d{1,}', lambda m: str(
                        int(round(float(m.group(0))))), centroid_ewkt)
            record.simplified_centroid_ewkt = simplified_centroid_ewkt

    def _compute_with_gis_link(self):
        geom_ok = self._geom_ok()
        for record in self:
            with_gis_link = False
            if geom_ok:
                self.env.cr.execute("""
                    SELECT """ + self._link_field + """
                    FROM """ + self._gis_table + """
                    WHERE """ + self._link_field + """='""" + record.name + """'
                    """)
                query_results = self.env.cr.dictfetchall()
                if (query_results and
                   query_results[0].get(self._link_field) is not None):
                    with_gis_link = True
            record.with_gis_link = with_gis_link

    def _search_with_gis_link(self, operator, value):
        record_ids = []
        operator_of_filter = 'in'
        with_gis_link = ((operator == '=' and value) or
                         (operator == '!=' and not value))
        geom_ok = self._geom_ok()
        if geom_ok:
            table = self._name.replace('.', '_')
            sql_statement = \
                'SELECT t.id FROM ' + table + ' t ' + \
                'INNER JOIN ' + self._gis_table + ' gt ' + \
                'ON t.name = gt.' + self._link_field
            if not with_gis_link:
                sql_statement = \
                    'SELECT t.id FROM ' + table + ' t ' + \
                    'LEFT JOIN ' + self._gis_table + ' gt ' + \
                    'ON t.name = gt.' + self._link_field + ' ' + \
                    'WHERE gt.gid IS NULL'
            self.env.cr.execute(sql_statement)
            sql_resp = self.env.cr.fetchall()
            if sql_resp:
                for item in sql_resp:
                    record_ids.append(item[0])
        return ([('id', operator_of_filter, record_ids)])

    def _compute_googlemaps_link(self):
        for record in self:
            googlemaps_link = ''
            srid, coordinates = record.extract_coordinates(
                record.simplified_centroid_ewkt)
            if srid and coordinates:
                srid = 'epsg:' + srid
                pos_bracketleft = coordinates.find('(')
                pos_bracketright = coordinates.find(')')
                pos_space = coordinates.find(' ')
                if (pos_bracketleft != -1 and pos_bracketright != -1 and
                   pos_space != -1 and pos_bracketleft < pos_space and
                   pos_space < pos_bracketright):
                    x_in = 0
                    y_in = 0
                    try:
                        x_in = int(coordinates[pos_bracketleft + 1:pos_space])
                        y_in = int(coordinates[pos_space + 1:pos_bracketright])
                    except Exception:
                        x_in = -1
                        y_in = -1
                    if x_in >= 0 and y_in >= 0:
                        in_proj = Proj(init=srid)
                        out_proj = Proj(init='epsg:4326')
                        x_out, y_out = transform(
                            in_proj, out_proj, x_in, y_in)
                        googlemaps_link = self._url_googlemaps.replace(
                            'ycval', str(y_out)).replace('xcval', str(x_out))
            record.googlemaps_link = googlemaps_link

    def _geom_ok(self):
        resp = True
        try:
            self.env.cr.execute(
                'SELECT ' + self._link_field + ', ' + self._geom_field + ' ' +
                'FROM ' + self._gis_table + ' LIMIT 1')
        except Exception:
            self.env.cr.rollback()
            resp = False
        return resp

    @api.model
    def extract_coordinates(self, geom_ewkt):
        srid = ''
        coordinates = ''
        if geom_ewkt:
            pos_semicolon = geom_ewkt.find(';')
            if pos_semicolon != -1 and pos_semicolon < len(geom_ewkt) - 1:
                coordinates = geom_ewkt[pos_semicolon + 1:]
                srid_temp = geom_ewkt[0:pos_semicolon]
                pos_equal = srid_temp.find('=')
                if pos_equal and pos_equal < len(srid_temp) - 1:
                    srid = srid_temp[pos_equal + 1:]
                if not srid:
                    coordinates = ''
        return srid, coordinates

    @api.model
    def extract_bounding_box(self, geom_ewkt):
        bounding_box = []
        srid, coordinates = self.extract_coordinates(geom_ewkt)
        if coordinates:
            coordinates = coordinates.lower()
            points = ''
            if coordinates.find('multipolygon') != -1:
                points = \
                    re.search(r'\(\(\((.*?)\)\)\)', coordinates).group(1)
            elif coordinates.find('polygon') != -1:
                points = \
                    re.search(r'\(\((.*?)\)\)', coordinates).group(1)
            if points:
                points = points.replace('),(', ', ').replace('), (', ', ')
                points = points.replace(', ', ',')
                list_of_points = points.split(',')
                first_point = True
                for point in list_of_points:
                    coordinates = point.split(' ')
                    if len(coordinates) == 2:
                        x = float(coordinates[0])
                        y = float(coordinates[1])
                        if first_point:
                            first_point = False
                            minx = x
                            maxx = x
                            miny = y
                            maxy = y
                        else:
                            if x < minx:
                                minx = x
                            if x > maxx:
                                maxx = x
                            if y < miny:
                                miny = y
                            if y > maxy:
                                maxy = y
                bounding_box = [minx, miny, maxx, maxy]
        return srid, bounding_box

    @api.model
    def extension_and_schema_postgis_created(self):
        resp = False
        self.env.cr.execute("""
            SELECT EXISTS(SELECT * FROM pg_extension WHERE extname='postgis')
            AND EXISTS(SELECT * FROM information_schema.schemata WHERE
            schema_name='postgis')""")
        if self.env.cr.fetchone()[0]:
            resp = True
        return resp

    @api.model
    def create_gis_table(self, gis_table,
                         geom_type='MULTIPOLYGON', epsg=25830):
        if not self._existing_gis_table(gis_table):
            gis_sequence = gis_table + '_gid_seq'
            gis_pkey = gis_table + '_pkey'
            gis_epsg = str(epsg)
            gis_index = gis_table + '_idx'
            self.env.cr.execute("""
                CREATE SEQUENCE IF NOT EXISTS
                    public.""" + gis_sequence + """
                    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647
                    CACHE 1;""")
            self.env.cr.execute("""
                CREATE TABLE IF NOT EXISTS
                    public.""" + gis_table + """(gid INTEGER NOT NULL
                    DEFAULT nextval('""" + gis_sequence + """'::regclass),
                    name CHARACTER VARYING(254) NOT NULL
                    COLLATE pg_catalog."default",
                    geom postgis.GEOMETRY
                    (""" + geom_type + """,""" + gis_epsg + """),
                    UNIQUE(name), CHECK (name <> ''),
                    CONSTRAINT """ + gis_pkey + """ PRIMARY KEY (gid));""")
            self.env.cr.execute("""
                CREATE INDEX
                IF NOT EXISTS """ + gis_index + """ ON
                public.""" + gis_table + """ USING gist (geom);""")
            self.env.cr.commit()

    def _existing_gis_table(self, gis_table):
        resp = False
        self.env.cr.execute("""
            SELECT EXISTS(SELECT * FROM information_schema.tables
            WHERE table_name='""" + gis_table + """')""")
        if self.env.cr.fetchone()[0]:
            resp = True
        return resp

    def get_aerial_image(self,
                         image_wms='https://www.ign.es/wms-inspire/pnoa-ma',
                         image_layers='OI.OrthoimageCoverage',
                         image_styles='default',
                         image_width=0,
                         image_height=824,
                         image_format='jpeg',
                         image_zoom=1.2,
                         image_with_filter=False):
        aerial_images = []
        # Number of layers passed
        number_of_layers = len(image_layers.split(',')) - 1
        for record in self:
            image = None
            srid, bounding_box = record.extract_bounding_box(
                record.geom_ewkt)
            if srid and bounding_box:
                bounding_box_final, image_width_pixels, image_height_pixels = \
                    self.get_bbox_final(image_zoom, bounding_box,
                                        image_width, image_height)
                if image_width_pixels > 0 and image_height_pixels > 0:
                    minx = bounding_box_final[0]
                    miny = bounding_box_final[1]
                    maxx = bounding_box_final[2]
                    maxy = bounding_box_final[3]
                    cql_filter = ''
                    if (image_with_filter):
                        cql_filter = '&FILTER=' + '()' * number_of_layers + \
                            '(<Filter><PropertyIsLike wildCard="*" ' + \
                            'singleChar="." escape="!">' + \
                            '<PropertyName>' + self._link_field + \
                            '</PropertyName><Literal>' + record.name + \
                            '</Literal></PropertyIsLike></Filter>)'
                    url = image_wms + '?service=wms' + \
                        '&version=1.3.0&request=getmap&crs=epsg:' + str(srid) + \
                        '&bbox=' + str(minx) + ',' + str(miny) + ',' + \
                        str(maxx) + ',' + str(maxy) + \
                        '&width=' + str(image_width_pixels) + \
                        '&height=' + str(image_height_pixels) + \
                        '&layers=' + image_layers + \
                        '&styles=' + image_styles + \
                        cql_filter + \
                        '&format=image/' + image_format
                    request_ok = True
                    try:
                        resp = requests.get(url, stream=True)
                    except Exception:
                        request_ok = False
                    if request_ok and resp.status_code == 200:
                        image_raw = io.BytesIO(resp.raw.read())
                        # When XML error returns a 200, but not image on raw
                        # Check before returning
                        try:
                            Image.open(image_raw)
                            image = base64.b64encode(image_raw.getvalue())
                        except Exception:
                            image = None
            aerial_images.append(image)
        if (all(i is None for i in aerial_images)):
            return None
        else:
            if len(aerial_images) == 1:
                aerial_images = aerial_images[0]
        return aerial_images

    @api.model
    def get_bbox_final(self, zoom, bbox_initial,
                       image_width_initial, image_height_initial):
        bbox_final = [0, 0, 0, 0]
        image_width_final = 0
        image_height_final = 0
        if (bbox_initial and len(bbox_initial) == 4
           and image_width_initial >= 0 and image_height_initial >= 0):
            minx = bbox_initial[0]
            miny = bbox_initial[1]
            maxx = bbox_initial[2]
            maxy = bbox_initial[3]
            image_width_meters = maxx - minx
            image_height_meters = maxy - miny
            if (image_width_meters > 0 and image_height_meters > 0 and
               zoom >= 1):
                new_image_width_meters = \
                    image_width_meters * zoom
                new_image_height_meters = \
                    image_height_meters * zoom
                dif_width_meters = \
                    new_image_width_meters - image_width_meters
                dif_height_meters = \
                    new_image_height_meters - image_height_meters
                offset_width_meters = dif_width_meters / 2
                offset_height_meters = dif_height_meters / 2
                minx = int(round(minx - offset_width_meters))
                miny = int(round(miny - offset_height_meters))
                maxx = int(round(maxx + offset_width_meters))
                maxy = int(round(maxy + offset_height_meters))
                if image_width_initial == 0 and image_height_initial == 0:
                    image_height_initial = self.NORMAL_SIZE
                image_width_meters = maxx - minx
                image_height_meters = maxy - miny
                image_height_pixels = image_height_initial
                image_width_pixels = image_width_initial
                if image_width_pixels == 0 or image_height_pixels == 0:
                    if image_width_pixels == 0:
                        image_width_pixels = int(round((
                            image_width_meters * image_height_pixels) /
                            image_height_meters))
                    else:
                        image_height_pixels = int(round((
                            image_height_meters * image_width_pixels) /
                            image_width_meters))
                bbox_final = [minx, miny, maxx, maxy]
                image_width_final = image_width_pixels
                image_height_final = image_height_pixels
        return bbox_final, image_width_final, image_height_final

    def contains_point(self, x, y):
        self.ensure_one()
        resp = False
        self.env.cr.execute("""
            SELECT gid FROM """ + self._gis_table + """
            WHERE postgis.st_contains(""" + self._geom_field + """
            , postgis.st_setsrid(postgis.st_point(""" + str(x) + """
            , """ + str(y) + """), postgis.st_srid(""" + self._geom_field + """
            ))) and name = '""" + self.name + """'""")
        query_results = self.env.cr.dictfetchall()
        if (query_results and query_results[0].get('gid') > 0):
            resp = True
        return resp

    def action_regenerate_shp(self, path_frompgtoshp=''):
        notification_response = ''
        if (not path_frompgtoshp):
            notification_response = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('The "Path of frompgtoshp" parameter '
                                 'is not populated.'),
                    'sticky': False,
                    'type': 'danger', }
            }
        else:
            regenerate_ok = self._regenerate_shp(path_frompgtoshp)
            if (regenerate_ok):
                notification_response = {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('GIS data updated.'),
                        'sticky': False,
                        'type': 'success', }
                }
            else:
                notification_response = {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error'),
                        'message': _('GIS data not updated.'),
                        'sticky': False,
                        'type': 'danger', }
                }
        return notification_response

    def _regenerate_shp(self, path_frompgtoshp):
        args = path_frompgtoshp.split()
        args.append(self.env.cr.dbname)
        returncode = subprocess.call(args)
        return (returncode == 0)
