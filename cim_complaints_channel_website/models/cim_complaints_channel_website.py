# -*- coding: utf-8 -*-
# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _


DEFAULT_LEGAL_BODY_HTML = (
    u"La legitimación se basa en el cumplimiento de una obligación legal "
    u"derivada de la Ley 2/2023, de conformidad con lo establecido en el "
    u"artículo 6.1.C. del Reglamento UE 679/2016 General de Protección de "
    u"Datos. El tratamiento de categorías especiales de datos personales por "
    u"razones de un interés público general se podrá realizar conforme a lo "
    u"establecido en el artículo 9.2.g del mismo Reglamento."
    u"<br/><br/>"
    u"Los datos personales recabados en el marco del canal de denuncias serán "
    u"los estricta y objetivamente necesarios para tramitar las denuncias "
    u"recibidas y, en su caso, investigar los hechos denunciados, y de acuerdo "
    u"a si el informante ha decidido o no revelar su identidad. En caso de haber "
    u"optado por identificarse, sus datos serán tratados con esa exclusiva "
    u"finalidad y no serán utilizados para finalidades incompatibles, salvo "
    u"excepciones contempladas legalmente como, por ejemplo, cuando su finalidad "
    u"sea la de conservación para dejar evidencia del funcionamiento del sistema. "
    u"Se hace constar expresamente que el derecho de acceso está limitado a los "
    u"propios datos de carácter personal."
    u"<br/><br/>"
    u"En cuanto a la comunicación a terceros, se informa que la información de "
    u"la denuncia, su contexto e investigación será tratada únicamente por el "
    u"Responsable del Canal de Denuncias y, en su caso, podrá comunicarse al "
    u"Delegado de Protección de Datos, al responsable de Recursos Humanos, al "
    u"responsable de los servicios jurídicos de la entidad o a la entidad "
    u"externa que pudiera tener delegada la gestión del Canal de Denuncias."
    u"<br/><br/>"
    u"También se comunicará a las autoridades que por sus competencias abran "
    u"expedientes de investigación o disciplinarios al respecto, así como a "
    u"las autoridades policiales o judiciales que por sus competencias abran "
    u"la investigación o el ejercicio de acciones legales. Los plazos de "
    u"conservación de los datos personales serán los establecidos en el "
    u"artículo 32 de la Ley 2/2023 o la que se establezca en la misma en caso "
    u"de futuras modificaciones de la normativa."
    u"<br/><br/>"
    u"La persona denunciante o cualquier otra persona interesada en el "
    u"procedimiento podrán ejercitar sus derechos de acceso, rectificación, "
    u"supresión, limitación, oposición y portabilidad en relación con sus datos "
    u"de carácter personal, así como presentar una reclamación ante la autoridad "
    u"de control competente."
)


class CimComplaintsChannelWebsite(models.Model):
    _name = 'cim.complaints.channel.website'
    _description = 'Complaints channel website legal configuration'

    name = fields.Char(
        string='Name',
        required=True,
        default=lambda self: _('Complaints Channel Website'),
    )

    active = fields.Boolean(
        string='Active',
        default=True,
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.user.company_id.id,
        ondelete='restrict',
    )

    responsible_name = fields.Char(
        string='Responsible Entity Name',
        related='company_id.name',
        readonly=True,
    )

    responsible_vat = fields.Char(
        string='NIF/VAT',
        related='company_id.vat',
        readonly=True,
    )

    responsible_phone = fields.Char(
        string='Phone',
        related='company_id.phone',
        readonly=True,
    )

    responsible_address = fields.Char(
        string='Address',
        compute='_compute_responsible_address',
        readonly=True,
    )

    legal_body_html = fields.Html(
        string='Legal body text',
        default=DEFAULT_LEGAL_BODY_HTML,
        sanitize=False,
    )

    _sql_constraints = [
        ('cim_ccw_company_uniq',
         'UNIQUE(company_id)',
         'Only one website legal configuration is allowed per company.'),
    ]

    @api.depends(
        'company_id',
        'company_id.street',
        'company_id.street2',
        'company_id.city',
        'company_id.zip',
        'company_id.state_id',
        'company_id.country_id',
    )
    def _compute_responsible_address(self):
        for record in self:
            partner = record.company_id and record.company_id.partner_id or False
            if not partner:
                record.responsible_address = ''
                continue
            chunks = []
            if partner.street:
                chunks.append(partner.street)
            if partner.street2:
                chunks.append(partner.street2)
            city_line_parts = []
            if partner.zip:
                city_line_parts.append(partner.zip)
            if partner.city:
                city_line_parts.append(partner.city)
            if city_line_parts:
                chunks.append(' '.join(city_line_parts))
            if partner.state_id and partner.state_id.name:
                chunks.append(partner.state_id.name)
            if partner.country_id and partner.country_id.name:
                chunks.append(partner.country_id.name)
            record.responsible_address = ', '.join(chunks)
