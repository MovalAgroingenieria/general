# -*- coding: utf-8 -*-
# 2020 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
import unicodedata
from datetime import datetime


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    entity_code = fields.Selection([
        ("200", "200 - Agost - C.R. L’Alcavonet"),
        ("201", "201 - Agost - C.R. Virgen de la Paz"),
        ("202", "202 - Agres - C.R. de Agres"),
        ("203", "203 - Albatera - C.R. de Albatera"),
        ("204", "204 - Albatera - Sindicato Local de Riegos de la Huerta"),
        ("205", "205 - Alcalalí - C.R. de Alcalalí-Xaló"),
        ("206", "206 - Algorfa - C.R. Virgen del Carmen"),
        ("207", "207 - Algueña - SAT 7566 Riegos La Algueña"),
        ("208", "208 - Alicante - C.R. de Alicante"),
        ("209", "209 - Almoradí - "
         "Juzgado Privativo de Aguas del Azud de Alfeitami"),
        ("210", "210 - Altea - C.R. de Altea la Vella"),
        ("211", "211 - Altea - C.R. Riego de la Pila y Cap Negret"),
        ("212", "212 - Altea - C.R. Riego Mayor y de Debajo de Altea"),
        ("213", "213 - Altea - C.R. Riego de Pere Chaume"),
        ("214", "214 - Altea - C.R. Riego Nuevo"),
        ("215", "215 - Aspe - C.R. Virgen de las Nieves"),
        ("216", "216 - Banyeres de Mariola - C.R. Riego Mayor de la Villa"),
        ("218", "218 - Beneixama - C.R. Valle de Beneixama"),
        ("219", "219 - Beneixama - C.R. Almizra"),
        ("220", "220 - Benejúzar - C.R. Los Rubes"),
        ("221", "221 - Benejúzar - C.R. San Pedro-Lo Maté"),
        ("222", "222 - Benejúzar - C.R. La Pilarica"),
        ("223", "223 - Benferri - C.R. de Benferri"),
        ("224", "224 - Benferri - C.R. de Las Cuevas"),
        ("225", "225 - Beniarbeig - C.R. Hortes de Baix"),
        ("226", "226 - Beniarbeig - C.R. Els Plans"),
        ("227", "227 - Beniarbeig - C.R. La Acequia de los Comunes"),
        ("228", "228 - Beniardá - C.R. y Usuarios La Font Benialet"),
        ("229", "229 - Beniarrés - C.R. de la Huerta de Benillup"),
        ("230", "230 - Benidorm - Sindicato Canal Bajo del Algar"),
        ("231", "231 - Benidorm - C.R. Canal Bajo del Algar"),
        ("232", "232 - Benigembla - C.R. Benigembla"),
        ("233", "233 - Benijófar - Juzgado Privativo de Aguas"),
        ("234", "234 - Benimantell - C.R. Font del Molí d ́Ondara"),
        ("235", "235 - Benimeli - C.R. de Benimeli"),
        ("236", "236 - Biar - C.R. San Cristobal-Biar"),
        ("237", "237 - Biar - C.R. Borrel-Pontarro"),
        ("238", "238 - Bigastro - C.R. San Joaquin Nuevos Riegos"),
        ("239", "239 - Bigastro - C.R. Santo Domingo de Bigastro"),
        ("240", "240 - Bolulla - C.R. Riego de Bolulla"),
        ("241", "241 - Bolulla - C.R. Fuente del Salt"),
        ("242", "242 - Callosa d'en Sarriá - "
         "Cdad.Gral. de Regants i Usuaris"),
        ("243", "243 - Callosa de Segura - Juzgado Privativo de Aguas"),
        ("244", "244 - Cañada - SAT 6830 Baldona"),
        ("245", "245 - Castalla - C.R. La Foia de Castalla"),
        ("246", "246 - Catral - C.R. de Catral"),
        ("247", "247 - Catral - Sindicato de Riegos de Catral"),
        ("248", "248 - Cocentaina - "
         "C.R. Pla de la Font Jovades Alcudia y Reg Sic"),
        ("249", "249 - Cocentaina - "
         "C.R. Viver de L ́Horta de Fraga y Real Blanc"),
        ("362", "362 - Cocentaina - "
         "C.R. de la Acequia de Calandria, Benideu y Bolta de Callosa"),
        ("363", "363 - Cocentaina - C.R. Beniaset-Algars de Cocentaina"),
        ("252", "252 - Cocentaina - C.R. de Bolta de Rosidol"),
        ("253", "253 - Cocentaina - C.R. de Terrache-Foya-Furianes"),
        ("254", "254 - Cocentaina - C.R. de Duque de Medinaceli"),
        ("255", "255 - Cox - Sindicato Local de Riegos"),
        ("256", "256 - Cox - "
         "Sindicato Gral. de Riegos de la Acequia de Cox-Albatera-Granja"),
        ("257", "257 - Crevillent - "
         "C.R. Km.35 Toma 12 del Trasvase (Canal margen izda)"),
        ("258", "258 - Crevillent - C.R. Los Fontes"),
        ("259", "259 - Crevillent - C.R. San Cayetano de Crevillent"),
        ("260", "260 - Crevillent - C.R. San Felipe Neri"),
        ("261", "261 - Daya Vieja - C.R. Acequia de Daya Vieja"),
        ("262", "262 - Denia - C.R. Pinella y Casablanca"),
        ("263", "263 - Dolores Sindicato Gral. de Aguas Dolores"),
        ("264", "264 - El Verger - "
         "C.R. Agricultores de Verger, Aguas y Riegos"),
        ("265", "265 - El Verger - "
         "C.R. de la Acequia de Verger, Setla y Mirarrosa"),
        ("266", "266 - Elda - C.R. Elda"),
        ("267", "267 - Els Poblets - C.R. Virgen del Socorro"),
        ("268", "268 - Elx - C.R. El Canal"),
        ("269", "269 - Elx - C.G de Regantes Riegos de Levante LS"),
        ("270", "270 - Elx - C.R. de Carrizales"),
        ("271", "271 - Elx - C.R. Tercero de Levante"),
        ("272", "272 - Elx - SAT 2281 San Enrique"),
        ("273", "273 - Elx - C.R. San Pascual"),
        ("274", "274 - Elx - C.R. Riegos el Porvenir"),
        ("275", "275 - Elx - C.R. Azud del Comuns"),
        ("276", "276 - Elx - C.R. Sexta y Séptima Elevación de Elche"),
        ("277", "277 - Elx - C.R. Cuarto de Levante y Séptima de la Peña"),
        ("278", "278 - Elx - C.R. de Bacarot"),
        ("279", "279 - Finestrat - C.R. de Finestrat"),
        ("280", "280 - Formentera de Segura - Juzgado Privativo de Aguas"),
        ("281", "281 - Granja de Rocamora - "
         "Sindicato local de riegos de Granja de Rocamora"),
        ("282", "282 - Guardamar - "
         "C.R. Riegos de Levante en la Margen Dcha. del Rio Segura"),
        ("283", "283 - Guardamar - Juzgado Privativo de Aguas"),
        ("284", "284 - Hondón de las Nieves - "
         "SAT 3539 Riegos de Hondón de las Nieves "),
        ("285", "285 - Hondón de los Frailes - "
         "Comisión Mixta H.F. S.Antón y S.Isidro "),
        ("286", "286 - Ibi - C.R. Santa María"),
        ("287", "287 - Ibi - C.R. Sagarest"),
        ("288", "288 - Jacarilla - C.R. Fuensanta"),
        ("289", "289 - Jacarilla - C.R. Ntra Sra. de Belen"),
        ("290", "290 - La Nucía - "
         "C.R. Riego Mayor de Alfaz del Pí y Benidorm"),
        ("291", "291 - La Nucía - C.R. del Armaig"),
        ("292", "292 - La Nucía - C.R. del Planet"),
        ("293", "293 - La Nucía - C.R. de Sentenilla de Baix"),
        ("294", "294 - La Nucía - C.R. de Sentenilla de Dalt"),
        ("295", "295 - La Romana - Coop. Riegos La Romana C.Val"),
        ("296", "296 - La Romana - C.R. La Romana"),
        ("297", "297 - La Romana - SAT 5914 Casas de Juan Blanco"),
        ("298", "298 - La Vila Joiosa - C.R. de Villajoyosa"),
        ("299", "299 - L'Orxa - C.R. de L'Orxa"),
        ("300", "300 - Monforte del Cid - C.R. Monforte del Cid"),
        ("301", "301 - Monovar - SAT 1780 Alciri"),
        ("302", "302 - Monovar - SAT 3509 Percamp"),
        ("303", "303 - Monovar - C.R. Chinorlet-Monóvar"),
        ("304", "304 - Murla - C.R. San Miguel"),
        ("305", "305 - Muro de Alcoy - "
         "C.R. San Joaquin de Cela de Nuñez y Alcocer de Planes"),
        ("306", "306 - Mutxamel - "
         "C.R. Sindicato de Riegos de la Huerta de Alicante"),
        ("307", "307 - Novelda - Cdad. de Aguas de Novelda"),
        ("308", "308 - Novelda - C.R. Monteagudo"),
        ("309", "309 - Ondara - C.R. de la Villa de Ondara"),
        ("310", "310 - Orihuela - Juzgado Privativo de Aguas"),
        ("311", "311 - Orihuela - C.R. La Murada Norte"),
        ("312", "312 - Orihuela - C.R. San Onofre-Torremendo"),
        ("313", "313 - Orihuela - C.R. Lo Marqués"),
        ("314", "314 - Orihuela - C.R. El Mojón"),
        ("315", "315 - Orihuela - "
         "C.R. Pozo de Ntra. Sra.del Perpetuo Socorro"),
        ("316", "316 - Orihuela - C.R. Zona 4º Canal de Poniente"),
        ("317", "317 - Orihuela - C.R. El Granjero"),
        ("318", "318 - Orxeta - "
         "C.R. El Granjero 317C.R. del Riego Mayor de la Huerta de Orxeta"),
        ("319", "319 - Parcent - C.R. y Usuarios del Vall del Pop "),
        ("320", "320 - Pedreguer - C.R. de Pedreguer y Caragús"),
        ("321", "321 - Pego - C.R. Pego y Tierras Arrozales"),
        ("322", "322 - Pilar de la Horadada - "
         "C.R. Margen Dcha. Pilar Horadada"),
        ("323", "323 - Pinoso - C.R. Hondón-Monóvar"),
        ("324", "324 - Pinoso - SAT 3481 Aguas de Pinoso"),
        ("325", "325 - Pinoso - SAT 3505 Santa Barbara"),
        ("326", "326 - Planes - C.R. La Vall de Planes"),
        ("327", "327 - Polop - C. Riegos Cotelles"),
        ("328", "328 - Polop - C.R. Riego Mayor de Polop"),
        ("329", "329 - Rafol de Almunia - C.R. Pozo de San Fco. de Paula"),
        ("330", "330 - Relleu - Cdad. de Riego Mayor"),
        ("331", "331 - Rojales - C.R. La Iniciativa"),
        ("332", "332 - Rojales Juzgado Privativo de Aguas"),
        ("333", "333 - Sagra - C.R. Racó Mortits"),
        ("334", "334 - Salinas - C.R. Salinas"),
        ("335", "335 - San Fulgencio - Sindicato Gral. de Aguas"),
        ("336", "336 - San Isidro - C.R. San Isidro y Realengo"),
        ("337", "337 - San Miguel de Salinas - C.R. San Miguel"),
        ("338", "338 - San Miguel de Salinas - C.R. Campo de Salinas"),
        ("339", "339 - Sant Vicent del Raspeig - C.R. Alicante Norte"),
        ("340", "340 - Sant Vicent del Raspeig - "
         "Cdad. Gral. de Regantes 'Aralvi'"),
        ("341", "341 - Sax - Sindicato Riegos Sax"),
        ("342", "342 - Sella - Cdad. Gral. de Regantes"),
        ("343", "343 - Sella - C.R. Azud de Murtera"),
        ("344", "344 - Sella - C.R. Azud de Toll del Molí"),
        ("345", "345 - Sella - C.R. El Azud del Ters"),
        ("346", "346 - Tárbena - C.R. Font del Hort"),
        ("347", "347 - Tárbena - C.R. Font de la Murta"),
        ("348", "348 - Tárbena - C.R. Casivañes"),
        ("349", "349 - Torrevieja - C.R. Torre Miguel"),
        ("350", "350 - Vall de Gallinera - C.R. Mineola"),
        ("351", "351 - Vall de Gallinera - Cdad. de Usuaris de La Vall"),
        ("352", "352 - Villena - C.R. de la Huerta y Partidas"),
        ("353", "353 - Villena - C.R. La Armonía"),
        ("354", "354 - Villena - C.R. El Pinar Alto"),
        ("355", "355 - Villena - C.R. San Cristobal, Villena y Cañada"),
        ("356", "356 - Villena - SAT 3495 Pinar Bajo"),
        ("357", "357 - Villena - C.R. Boquera-Carboneras"),
        ("358", "358 - Villena - SAT 3565 El Puerto"),
        ("359", "359 - Villena - C.R. de Villena"),
        ("364", "364 - Villena - C. Gral. del Alto Vinalopó de Villena"),
        ("360", "360 - Xaló - C.R. de Xaló"),
        ("361", "361 - Xixona - C.R. de Xixona")],
        string="Entity Code",
        help="This code identifies the entity that sends the delegated "
             "charge to SUMA")

    @api.multi
    def set_entity_code_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'entity_code', self.entity_code)


class BankPaymentLine(models.Model):
    _inherit = 'bank.payment.line'

    suma_ref = fields.Char(
        string="SUMA reference",
        readonly=True,
        help="This number indicates the payment reference if it has "
             "been made by SUMA")

    suma_sent = fields.Boolean(
        string="SUMA done",
        readonly=True,
        help="Indicates whether this payment has already been added "
             "to an SUMA payment file")


class AccountPaymentOrder(models.Model):
    _inherit = 'account.payment.order'

    ENCODING_NAME = '8859'
    ENCODING_TYPE = 'replace'

    def _get_entity_config_suma(self):
        code = self.env['ir.values'].get_default('account.config.settings',
                                                 'entity_code')
        if code:
            entity = dict(self.env['account.config.settings'].fields_get(
                allfields=['entity_code'])['entity_code']['selection'])[code]
        else:
            entity = "Unconfigured"
        return entity

    # Error mode
    error_mode = fields.Selection([
        ('strict', 'Strict'),
        ('permissive', 'Permissive')],
        string="Error mode",
        default="strict",
        help="Strict mode does not allow errors. The permissive mode allows "
             "but they are collected in the 'Errors' tab.' This applies to "
             "both payment file and direct debit file")

    # Errors tab
    errors_found = fields.Text('Errors', readonly=True)

    # Fields
    payment_mode_name = fields.Char(
        compute='_compute_payment_mode_name',
        string="Payment mode name")

    entity = fields.Char(
        string="Entity",
        default=_get_entity_config_suma,
        compute="_compute_entity",
        readonly=True,
        help="This code identifies the entity that sends the delegated "
             "charge to SUMA.\nThis parameter is set in the accounting "
             "configuration")

    charge_type = fields.Selection([
        ('V', 'Volunteer'),
        ('E', 'Executive')],
        string="Charge type",
        help="Period in which debts should be managed", default="V")

    entity_type_code = fields.Selection([
        ('A', 'Town hall'),
        ('C', 'Water user assotiation')],
        string="Entity type",
        readonly=False,
        store=True,
        compute="get_entity_type_code",
        help="The type of entity")

    charge_year = fields.Selection([
        ('2019', '2019'),
        ('2020', '2020'),
        ('2021', '2021'),
        ('2022', '2022'),
        ('2023', '2023'),
        ('2024', '2024'),
        ('2025', '2025'),
        ('2026', '2026'),
        ('2027', '2027'),
        ('2028', '2028'),
        ('2029', '2029')],
        string="Charge year",
        help="The year in which the charge is charged",
        default="2019")

    concept = fields.Selection([
        ('AO', 'AO - WATER CONSUMPTION IRRIGATION AND DRIP'),
        ('AP', 'AP - DRINKING WATERS'),
        ('D1', 'D1 - FEES AND SPILLS'),
        ('D2', 'D2 - MAINTENANCE SPILLS'),
        ('D3', 'D3 - JUCARVINALOPO TRASVASE SPILL'),
        ('D4', 'D4 - MODERNIZATION FEES IRRIGATIONS'),
        ('D5', 'D5 - IRRIGATIONS MADE BY PARTICIPANTS'),
        ('D6', 'D6 - SERVICES PROVIDED BY PARTICIPANTS'),
        ('D7', 'D7 - FEES MAINTENANCE ACUEDUCTSS'),
        ('MJ', 'MJ - IRRIGATION PENALTIES AND SANCTIONS')],
        string="Concept",
        help="Concept by which the settlement or receipt is made.\nIt will "
             "be applied to all transactions",
        default="AO")

    concept_description = fields.Char(
        string="Concept description",
        compute="_compute_concept_description",
        readonly=True)

    charge_issuance = fields.Selection([
        ('01', '01 (volunteer)'),
        ('02', '02 (volunteer)'),
        ('03', '03 (volunteer)'),
        ('04', '04 (volunteer)'),
        ('05', '05 (volunteer)'),
        ('06', '06 (volunteer)'),
        ('07', '07 (volunteer)'),
        ('08', '08 (volunteer)'),
        ('09', '09 (volunteer)'),
        ('10', '10 (volunteer)'),
        ('11', '11 (volunteer)'),
        ('12', '12 (volunteer)'),
        ('13', '13 (volunteer)'),
        ('14', '14 (volunteer)'),
        ('15', '15 (volunteer)'),
        ('16', '16 (executive)'),
        ('17', '17 (executive)'),
        ('18', '18 (executive)'),
        ('19', '19 (executive)'),
        ('20', '20 (executive)'),
        ('21', '21 (executive)'),
        ('22', '22 (executive)'),
        ('23', '23 (executive)'),
        ('24', '24 (executive)'),
        ('25', '25 (executive)')],
        string="Charge issuance",
        default="01",
        help="Used to differentiate charges in the same year\n"
             "The numbering will be correlative within the same year")

    periodicity = fields.Selection([
        ('A', 'ANNUAL'),
        ('S', 'BIANNUAL'),
        ('T', 'QUARTERLY'),
        ('M', 'MONTHLY'),
        ('B', 'BIMONTHLY'),
        ('C', 'FOUR-MONTHLY'),
        ('N', 'NUMBER OF QUARTERS')],
        string="Periodicity",
        default="A",
        help="Type of period settled.\nIt will be applied to all "
             "transactions")

    initial_period = fields.Selection([
        ('01', '01'),
        ('02', '02'),
        ('03', '03'),
        ('04', '04'),
        ('05', '05'),
        ('06', '06'),
        ('07', '07'),
        ('08', '08'),
        ('09', '09'),
        ('10', '10'),
        ('11', '11'),
        ('12', '12')],
        string="Initial period",
        default="01",
        help="The initial period depends on the periodicity. For example, "
             "first semester or quarter: 01; third quarter: 03.\nEmpty if "
             "the periodicity is annual")

    final_period = fields.Selection([
        ('01', '01'),
        ('02', '02'),
        ('03', '03'),
        ('04', '04'),
        ('05', '05'),
        ('06', '06'),
        ('07', '07'),
        ('08', '08'),
        ('09', '09'),
        ('10', '10'),
        ('11', '11'),
        ('12', '12')],
        string="Final period",
        default="01",
        help="The final period depends on the periodicity. For example, "
             "first semester or quarter: 01; third quarter: 03.\nEmpty "
             "if the periodicity is annual")

    # SUMA resume related fields
    suma_filename = fields.Char(string="suma filename")
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self:
                                  self.env.user.company_id.currency_id)
    suma_total_amount = fields.Monetary(string="SUMA total amount")

    # Methods
    @api.depends('payment_mode_id')
    def _compute_payment_mode_name(self):
        # @INFO: payment mode name SUMA (mandatory)
        for record in self:
            record.payment_mode_name = record.payment_mode_id.name

    # On change payment mode force date_prefered
    @api.onchange('payment_mode_name')
    def _onchange_payment_mode_name(self):
        if self.payment_mode_name == 'SUMA':
            self.date_prefered = 'due'

    # Set entity
    @api.depends('payment_mode_name')
    def _compute_entity(self):
        for record in self:
            record.entity = record._get_entity_config_suma()

    @api.depends('payment_mode_name', 'concept')
    def _compute_concept_description(self):
        for record in self:
            concept_desc = dict(
                self.env['account.payment.order'].fields_get(
                    allfields=['concept'])['concept']['selection']
                )[record.concept]
            record.concept_description = concept_desc

    # Warning user when charge issuance is not valid
    # INFO: Changed to 1-15 in volunteer in 2024.06.10
    @api.onchange('payment_mode_name', 'charge_issuance', 'charge_type')
    def _onchange_charge_issuance(self):
        if self.payment_mode_name == 'SUMA':
            if self.charge_type == "V":
                title = "Charge issuance error"
                if int(self.charge_issuance) > 15:
                    message = \
                        _("Charge issuance for volunteer period has to "
                          "be less than 16.")
                    warning = {'title': title, 'message': message}
                    return {'warning': warning}
            elif self.charge_type == "E":
                title = "Charge issuance error"
                if int(self.charge_issuance) < 16:
                    message = \
                        _("Charge issuance for executive period has to "
                          "be greater than 15.")
                    warning = {'title': title, 'message': message}
                    return {'warning': warning}

    # Warning user when initial and final periods are incompatible
    @api.onchange('payment_mode_name', 'periodicity',
                  'initial_period', 'final_period')
    def _onchange_per_ini_fin(self):
        if self.payment_mode_name == 'SUMA':
            if self.periodicity != "A":
                title = "Period range error"
                if self.periodicity == "S":
                    if int(self.initial_period) > 2 or \
                       int(self.final_period) > 2:
                        message = \
                            _("The biannual periodicity only accepts the "
                              "values 01 and 02, in both the initial and the "
                              "final period.")
                        warning = {'title': title, 'message': message}
                        return {'warning': warning}
                elif self.periodicity == "T":
                    if int(self.initial_period) > 4 or \
                       int(self.final_period) > 4:
                        message = \
                            _("The quarterly periodicity only accepts the "
                              "values 01 to 04, in both the initial and the "
                              "final period.")
                        warning = {'title': title, 'message': message}
                        return {'warning': warning}
                elif self.periodicity == "M":
                    if int(self.initial_period) > 12 or \
                       int(self.final_period) > 12:
                        message = \
                            _("The monthly periodicity only accepts the "
                              "values 01 to 12, in both the initial and the "
                              "final period.")
                        warning = {'title': title, 'message': message}
                        return {'warning': warning}
                elif self.periodicity == "B":
                    if int(self.initial_period) > 6 or \
                       int(self.final_period) > 6:
                        message = \
                            _("The bimonthly periodicity only accepts the "
                              "values 01 to 06, in both the initial and the "
                              "final period.")
                        warning = {'title': title, 'message': message}
                        return {'warning': warning}
                elif self.periodicity == "C":
                    if int(self.initial_period) > 3 or \
                       int(self.final_period) > 3:
                        message = \
                            _("The four-monthly periodicity only accepts the "
                              "values 01 to 03, in both the initial and the "
                              "final period.")
                        warning = {'title': title, 'message': message}
                        return {'warning': warning}
                elif self.periodicity == "N":
                    if int(self.initial_period) > 3 or \
                       int(self.final_period) > 3:
                        message = _("The number of quarters only accepts the "
                                    "values 01 to  03, in both the initial "
                                    "and the final period.")
                        warning = {'title': title, 'message': message}
                        return {'warning': warning}

    # Generate payment file
    @api.multi
    def generate_payment_file(self):
        self.ensure_one()
        _log = logging.getLogger(self.__class__.__name__)
        pay_method = self.payment_method_id

        if pay_method.code != 'debit_suma':
            return super(AccountPaymentOrder, self).generate_payment_file()

        # Declare error vars
        self.errors_found = ""
        errors = ""
        error_num = 0

        # Charges file
        # Charge type - Position [001-001] Length 1
        # @INFO: Only V (Volunteer) and E (Executive)
        charge_type = self.charge_type

        # Charge year - Position [002-005] Length 4
        charge_year = str(self.charge_year)

        # Alicante province INE code - Position [006-007] Length 2
        alicante_province_ine_code = "03"

        # Entity code - Position [008-010] Length 3
        if self.entity == 'Unconfigured':
            raise ValidationError(
                _("The entity has not been configured. Set it "
                  "in Accounting/Settings."))
        else:
            entity_code = self.env['ir.values'].get_default(
                'account.config.settings', 'entity_code')

        # Charge concept code - Position [011-012] Length 2
        concept_code = self.concept

        # Charge_issuance - Position [013-014] Length 2
        charge_issuance = str(self.charge_issuance)

        # Entity type code - Position [015-015] Length 1
        # @INFO: The method of this part is overridden by other modules as
        #        wua_account_banking_suma_wua
        entity_type_code = self.get_entity_type_code()

        # Value type - Position [016-016] Length 1
        value_type = "R"

        # Value number - Position [017-022] Length 6
        # @INFO: It must contain the receipt list reference within the register
        #        There cannot be repeated numbers within the same register
        #        It must always be informed and it cannot be all zeros
        # entry_num = (in the loop)

        # Internal reference - Position [023-037] Length 15
        # @INFO: It is optional, but it will be stored by
        #        receiving entity (SUMA) and can be used
        #        to reference value movements.
        # internal_ref = (in the loop)

        # Taxpayer type - Position [038-038] Length 1
        # @INFO: F for physical person or J for legal person
        # taxpayer_type = (in the loop)

        # Taxpayer name - Position [039-098] Length 60
        # taxpayer_name = (in the loop)

        # Taxpayer address type - Position [099-100] Length 2
        # @INFO: Only 04 address format is used
        taxpayer_address_type = "04"

        # Taxpayer address - Position [101-161] Length 61
        # Fields in 04 format:
        #  Street type        Position [101-102] Length  2
        #  Street name        Position [103-122] Length 20
        #  Street number      Position [123-127] Length  5
        #  Street description Position [128-134] Length  7
        #  County code        Position [135-137] Length  3
        #  County INE code    Position [138-140] Length  3
        #  Province INE code  Position [141-142] Length  2
        #  Blank space        Position [143-161] Length 19

        # Amount for receipt - Position [162-171] Length 10
        # @INFO: in cents and padded up to 10
        # amount = (in the loop)

        # Taxpayer VAT - Position [172-181] Length 10
        # taxpayer_vat = (in the loop)

        # Value format type - Position [182-182] Length 1
        # @INFO: 3 - for receipt with a unique concept
        #        5 - for receipt with subconcepts
        value_format_type = "3"

        # Tax object - Position [183-222] Length 40
        # @INFO: only 03 value format is used
        # tax_object = (in the loop)

        # Fixed number - Position [223-234] Length 12
        # fixed_number = (in the loop)

        # Reset variables
        # @INFO: Accumulate cents (the exact value written to positions
        #        162-171) instead of euros so the Delivery Document total
        #        matches what SUMA reads from the file.
        total_amount_cents = 0
        bank_lines = ""
        entry_num = 0

        # Iterate over bank lines
        for line in self.bank_line_ids:

            # Value number
            entry_num += 1
            entry_num_padded = str(entry_num).zfill(6)

            # Check if bank line is already done by suma
            if line.suma_sent:
                if self.error_mode == 'permissive':
                    error_num += 1
                    errors += '[' + str(error_num).zfill(4) + '] ' + \
                        _("The entry number %s has failed, the bank line "
                          "%s seems that it has already been sent through "
                          "SUMA" % (entry_num_padded, line.name)) + '\n'
                else:
                    raise ValidationError(
                        _("The entry number %s has failed, the bank line "
                          "%s seems that it has already been sent through "
                          "SUMA" % (entry_num_padded, line.name)))

            # Internal reference - Position [023-037] Length 15
            # @INFO: This number is associate to each bank line
            #        Done in line write at the end of loop
            internal_ref = self.env['ir.sequence'].next_by_code(
                'suma_seq_internal_ref')
            # @INFO: Enforce exactly 15 chars to avoid record displacement
            internal_ref = str(internal_ref).zfill(15)[:15]

            # Taxpayer type - Position [038-038] Length 1
            if line.partner_id.company_type == 'company':
                taxpayer_type = "J"
            else:
                taxpayer_type = "F"

            # Taxpayer name - Position [039-098] Length 60
            # @INFO: lastname1 lastname2, firstname
            if line.partner_id.company_type == 'company':
                # @INFO: delete points and replace commas by spaces
                #        Limit and justify to 60 chars
                taxpayer_name = \
                    line.partner_id.name.replace(".",
                                                 "").replace(",", " ")[:60]
                taxpayer_name_padded = taxpayer_name.ljust(60)
            elif line.partner_id.company_type == 'person':
                # @INFO: partner_second_lastname dependence
                if line.partner_id.lastname:
                    taxpayer_name = line.partner_id.lastname
                    if line.partner_id.lastname2:
                        taxpayer_name += ' ' + line.partner_id.lastname2
                else:
                    if self.error_mode == 'permissive':
                        error_num += 1
                        errors += '[' + str(error_num).zfill(4) + '] ' + \
                            _("The entry number %s has failed, the lastname"
                              "for partner %s not found." %
                              (entry_num_padded, line.partner_id.name)) + '\n'
                    else:
                        raise ValidationError(
                            _("The entry number %s has failed, the lastname"
                              "for partner %s not found." %
                              (entry_num_padded, line.partner_id.name)))
                if line.partner_id.firstname:
                    taxpayer_name += ' ' + line.partner_id.firstname
                else:
                    if self.error_mode == 'permissive':
                        error_num += 1
                        errors += '[' + str(error_num).zfill(4) + '] ' + \
                            _("The entry number %s has failed, the firstname "
                              "for partner %s not found." %
                              (entry_num_padded, line.partner_id.name)) + '\n'
                    else:
                        raise ValidationError(
                            _("The entry number %s has failed, the firstname "
                              "for partner %s not found." %
                              (entry_num_padded, line.partner_id.name)))
                taxpayer_name_padded = taxpayer_name.ljust(60)
            else:
                if self.error_mode == 'permissive':
                    error_num += 1
                    errors += '[' + str(error_num).zfill(4) + '] ' + \
                        _("The entry number %s has failed, taxpayer name not "
                          "found." % (entry_num_padded)) + '\n'
                    taxpayer_name_padded = str(" " * 60)
                else:
                    raise ValidationError(
                        _("The entry number %s has failed, taxpayer name not "
                          "found." % (entry_num_padded)))

            # Taxpayer address type - Position [099-100] Length 2
            # taxpayer_address_type = (static, outside the loop)

            # Taxpayer address - Position [101-161] Length 61
            if taxpayer_address_type == "04":
                # Street type - Position [101-102] Length 2
                # @INFO: l10n_es_partner_street_type dependence
                if line.partner_id.street_type_id:
                    taxpayer_address_street_type = \
                        (line.partner_id.street_type_id.abbreviation
                         or "")[:2].ljust(2)
                else:
                    taxpayer_address_street_type = "CL"

                # Street name - Position [103-122] Length 20
                if line.partner_id.street:
                    taxpayer_address_street_name = \
                        line.partner_id.street[:20].ljust(20)
                else:
                    if self.error_mode == 'permissive':
                        error_num += 1
                        errors += '[' + str(error_num).zfill(4) + '] ' + \
                            _("The entry number %s has failed, taxpayer "
                              "street not found for partner %s" %
                              (entry_num_padded, line.partner_id.name)) + \
                            '\n'
                        taxpayer_address_street_name = str(" " * 20)
                    else:
                        raise ValidationError(
                            _("The entry number %s has failed, taxpayer "
                              "street not found for partner %s" %
                              (entry_num_padded, line.partner_id.name)))

                # Street number - Position [123-127] Length 5
                # @INFO: partner_address_street_number dependence
                if line.partner_id.street_num:
                    # Get only numbers, keep the last 5 digits and pad to
                    # exactly 5 to avoid overflowing the field (displacement)
                    street_num_digits = ''.join(
                        [x for x in line.partner_id.street_num
                         if x.isdigit()])
                    taxpayer_address_street_number = \
                        street_num_digits[-5:].zfill(5)
                else:
                    taxpayer_address_street_number = str(" " * 5)

                # Street description - Position [128-134] Length 7
                # @INFO: - It allows format Escalera(1), Piso(2), Puerta(2),
                #          Letra(1), Tipo(1)
                #        - The field street2 can be used
                taxpayer_address_street_description = str(" " * 7)

                # County code - Position [135-137] Length 3
                # @INFO: The last 3 zip numbers
                if line.partner_id.zip:
                    county_code = str(line.partner_id.zip[2:5]).zfill(3)
                    if not county_code.isdigit():
                        county_code = str(" " * 3)
                else:
                    if self.error_mode == 'permissive':
                        error_num += 1
                        errors += '[' + str(error_num).zfill(4) + '] ' + \
                            _("The entry number %s has failed, taxpayer zip "
                              "not found for partner %s" %
                              (entry_num_padded, line.partner_id.name)) + \
                            '\n'
                        county_code = str(" " * 3)
                    else:
                        raise ValidationError(
                            _("The entry number %s has failed, taxpayer zip "
                              "not found for partner %s" %
                              (entry_num_padded, line.partner_id.name)))

                # INE codes
                if line.partner_id.city:
                    city_name = ""
                    city_name2 = ""
                    city_name_simplified = ""
                    city_name_simplified2 = ""

                    if '(' in line.partner_id.city:
                        # Get name between parenthesis
                        city_name = line.partner_id.city[
                            line.partner_id.city.find(
                                "(")+1:line.partner_id.city.find(")")]
                        # Get name before parenthesis
                        city_name2 = line.partner_id.city.split('(')[0]
                    elif '/' in line.partner_id.city:
                        # Get name after bar
                        city_name = line.partner_id.city.split('/')[0]
                        # Get name before bar
                        city_name2 = line.partner_id.city.split('/')[1]
                    else:
                        city_name = line.partner_id.city

                    # Simplify city name to compare
                    city_name_simplified = \
                        unicodedata.normalize('NFKD', city_name).encode(
                            self.ENCODING_NAME,
                            self.ENCODING_TYPE).upper()

                    if city_name2:
                        city_name_simplified2 = \
                            unicodedata.normalize('NFKD', city_name2).encode(
                                self.ENCODING_NAME,
                                self.ENCODING_TYPE).upper()
                    else:
                        city_name_simplified2 = ""

                    # Get ine codes using partner city simplified
                    ine_codes = \
                        self.env[
                            'res.ine.code'].search(
                                ['|', '|', '|', '|', '|',
                                 ('city_name_simplified', '=',
                                  city_name_simplified),
                                 ('city_name_aka_simplified', '=',
                                  city_name_simplified),
                                 ('city_name_simplified', '=',
                                  city_name_simplified2),
                                 ('city_name_aka_simplified', '=',
                                  city_name_simplified2),
                                 ('city_name_reordered_simplified', '=',
                                  city_name_simplified),
                                 ('city_name_reordered_simplified', '=',
                                  city_name_simplified2)])

                    if ine_codes:
                        if len(ine_codes) > 1:
                            partner_zip = line.partner_id.zip
                            if partner_zip and len(partner_zip) > 2:
                                province_code = partner_zip[:2]
                                filtered_ine_codes = ine_codes.filtered(
                                    lambda code:
                                        code.ine_code_province == province_code
                                )
                                if filtered_ine_codes:
                                    ine_codes = filtered_ine_codes[0]
                                else:
                                    ine_codes = ine_codes[0]
                            else:
                                ine_codes = ine_codes[0]
                        # County INE code - Position [138-140] Length 3
                        county_ine_code = \
                            str(ine_codes.ine_code_city).zfill(3)
                        # Province INE code -  Position [141-142] Length 2
                        province_ine_code = \
                            str(ine_codes.ine_code_province).zfill(2)
                    else:
                        if self.error_mode == 'permissive':
                            error_num += 1
                            errors += '[' + str(error_num).zfill(4) + '] ' + \
                                _("The entry number %s has failed, taxpayer "
                                  "ine city code not found for city %s.\n"
                                  "Sometimes this is because the name of the "
                                  "city is not well written (first capital "
                                  "letter, accents, hyphens, etc.) or is the "
                                  "name of a district instead of a city." %
                                  (entry_num_padded, line.partner_id.city)) + \
                                '\n'
                            county_ine_code = str(" " * 3)
                            province_ine_code = str(" " * 2)
                        else:
                            raise ValidationError(
                                _("The entry number %s has failed, taxpayer "
                                  "ine city code not found for city %s.\n"
                                  "Sometimes this is because the name of the "
                                  "city is not well written (first capital "
                                  "letter, accents, hyphens, etc.) or is the "
                                  "name of a district instead of a city." %
                                  (entry_num_padded, line.partner_id.city)))
                else:
                    if self.error_mode == 'permissive':
                        error_num += 1
                        errors += '[' + str(error_num).zfill(4) + '] ' + \
                            _("The entry number %s has failed, debtor city "
                              "not found for partner %s" %
                              (entry_num_padded, line.partner_id.name)) + '\n'
                        county_ine_code = str(" " * 3)
                        province_ine_code = str(" " * 2)
                    else:
                        raise ValidationError(
                            _("The entry number %s has failed, debtor city "
                              "not found for partner %s" %
                              (entry_num_padded, line.partner_id.name)))

                # Blank space - Position [143-161] Length 19
                blank_space1 = str(" " * 19)

            else:
                if self.error_mode == 'permissive':
                    error_num += 1
                    errors += '[' + str(error_num).zfill(4) + '] ' + \
                        _("The entry number %s has failed, the address type "
                          "%s is not supported." %
                          (entry_num_padded, taxpayer_address_type)) + '\n'
                    taxpayer_address_type = " "
                else:
                    raise ValidationError(
                        _("The entry number %s has failed, the address type "
                          "%s is not supported." %
                          (entry_num_padded, taxpayer_address_type)))

            # Amount for receipt - Position [162-171] Length 10
            # @INFO: in cents and padded up to 10. Use round() to avoid float
            #        truncation errors (e.g. 19.99 * 100 -> 1998.99 -> 1998).
            amount_cents = int(round(line.amount_currency * 100))
            amount = str(amount_cents).zfill(10)[:10]

            # Sum amount to total_amount (for resume doc)
            # @INFO: Accumulate the exact cents written to positions 162-171
            #        so the Delivery Document total matches what SUMA reads.
            total_amount_cents += amount_cents

            # Taxpayer VAT - Position [172-181] Length 10
            # @INFO: The two first chars are sliced
            if line.partner_id.vat:
                taxpayer_vat = line.partner_id.vat[2:]
                if len(taxpayer_vat) > 9 or not \
                        line.partner_id.vat[3:-1].isdigit():
                    if self.error_mode == 'permissive':
                        error_num += 1
                        errors += '[' + str(error_num).zfill(4) + '] ' + \
                            _("The entry number %s has failed, the vat %s "
                              "for partner %s is not valid." %
                              (entry_num_padded, taxpayer_vat,
                               line.partner_id.name)) + '\n'
                        taxpayer_vat = str(taxpayer_vat).ljust(10)
                    else:
                        raise ValidationError(
                            _("The entry number %s has failed, the vat %s "
                              "for partner %s is not valid." %
                              (entry_num_padded, taxpayer_vat,
                               line.partner_id.name)))
                taxpayer_vat = str(taxpayer_vat)[:10].ljust(10)
            else:
                if self.error_mode == 'permissive':
                    error_num += 1
                    errors += '[' + str(error_num).zfill(4) + '] ' + \
                        _("The entry number %s has failed, vat not found "
                          "for partner %s." % (entry_num_padded,
                                               line.partner_id.name)) + '\n'
                    taxpayer_vat = str(" " * 10)
                else:
                    raise ValidationError(
                        _("The entry number %s has failed, vat not found "
                          "for partner %s." % (entry_num_padded,
                                               line.partner_id.name)))

            # Value format type - Position [182-182] Length 1
            # value_format_type = (static, outside the loop)

            # Tax object - Position [183-222] Length 40
            # @INFO: Short description of what is billed
            #        We get this from invoice num that becomes communication
            #        field in bank_line. Usually it's a simple number but if
            #        option group in payment mode is active it chains all names
            if value_format_type == "3":
                # @INFO: Initialize to safe defaults so the field keeps its
                #        exact length even if no payment line matches (avoids
                #        stale values from previous iterations / displacement)
                invoice = False
                tax_object = str(" " * 40)
                for l in line.payment_line_ids:
                    if line.name == l.bank_line_id.name:
                        invoice = l.invoice_id
                        if invoice and invoice.number:
                            tax_object = invoice.number[:40].ljust(40)
                        else:
                            tax_object = str(" " * 40)
            else:
                if self.error_mode == 'permissive':
                    error_num += 1
                    errors += '[' + str(error_num).zfill(4) + '] ' + \
                        _("The entry number %s has failed, the format "
                          "type %s is not supported." %
                          (entry_num_padded, value_format_type)) + '\n'
                    value_format_type = " "
                else:
                    raise ValidationError(
                        _("The entry number %s has failed, the format "
                          "type %s is not supported." %
                          (entry_num_padded, value_format_type)))

            # Fixed number - Position [223-234] Length 12
            # @INFO: This part is overwritten by other modules
            if line.partner_id:
                fixed_number = self.get_fixed_number(line.partner_id)
            else:
                if self.error_mode == 'permissive':
                    error_num += 1
                    errors += '[' + str(error_num).zfill(4) + '] ' + \
                        _("The entry number %s has failed, the partner id not "
                          "found for partner %s." % (entry_num_padded,
                                                     line.partner_id.name)) + \
                        '\n'
                    fixed_number = str(" " * 12)
                else:
                    raise ValidationError(
                        _("The entry number %s has failed, the partner id not "
                          "found for partner %s." % (entry_num_padded,
                                                     line.partner_id.name)))

            # Fiscal year - Position [235-238] Length 4
            # @INFO: Must be the budget/charge exercise year (charge_year) so
            #        it stays consistent with the Delivery Document and the
            #        declared periodicity. Deriving it per line from each
            #        invoice move date produced mismatched years (e.g. 2025
            #        instead of 2026) and broke automated validation.
            fiscal_year = str(self.charge_year)[:4].zfill(4)

            # Periodicity - Position [239-239] Length 1
            periodicity = self.periodicity

            # Initial period - Position [240-241] Length 2
            if self.periodicity == 'A':
                initial_period = str(" " * 2)
            else:
                initial_period = self.initial_period

            # Final period - Position [242-243] Length 2
            if self.periodicity == 'A':
                final_period = str(" " * 2)
            else:
                final_period = self.final_period

            # Detail lines (hook). Return detail lines
            line_detail_1, line_detail_2, line_detail_3, line_detail_4 = \
                self.create_details_lines(self.description, line, invoice)

            # Blank space - Position [544-643] Length 100
            blank_space2 = str(" " * 100)

            # Log bank line fields with length [and expected length]
            _log.info('NEW BANK LINE. Number %s #########################'
                      % str(entry_num).zfill(5))
            _log.info('BANK LINE FIELD Charge type       (length %s [001]): %s'
                      % (str(len(charge_type)).zfill(3), charge_type))
            _log.info('BANK LINE FIELD Charge year       (length %s [004]): %s'
                      % (str(len(charge_year)).zfill(3), charge_year))
            _log.info('BANK LINE FIELD Province code     (length %s [002]): %s'
                      % (str(len(alicante_province_ine_code)).zfill(3),
                         alicante_province_ine_code))
            _log.info('BANK LINE FIELD Entity code       (length %s [003]): %s'
                      % (str(len(entity_code)).zfill(3), entity_code))
            _log.info('BANK LINE FIELD Concept code      (length %s [002]): %s'
                      % (str(len(concept_code)).zfill(3), concept_code))
            _log.info('BANK LINE FIELD Charge issuance   (length %s [002]): %s'
                      % (str(len(charge_issuance)).zfill(3), charge_issuance))
            _log.info('BANK LINE FIELD Entity type code  (length %s [001]): %s'
                      % (str(len(entity_type_code)).zfill(3),
                         entity_type_code))
            _log.info('BANK LINE FIELD Value type        (length %s [001]): %s'
                      % (str(len(value_type)).zfill(3), value_type))
            _log.info('BANK LINE FIELD Value number      (length %s [006]): %s'
                      % (str(len(entry_num_padded)).zfill(3),
                         entry_num_padded))
            _log.info('BANK LINE FIELD Internal ref      (length %s [015]): %s'
                      % (str(len(internal_ref)).zfill(3), internal_ref))
            _log.info('BANK LINE FIELD Taxpayer type     (length %s [001]): %s'
                      % (str(len(taxpayer_type)).zfill(3), taxpayer_type))
            _log.info('BANK LINE FIELD Taxpayer name     (length %s [060]): %s'
                      % (str(len(taxpayer_name_padded)).zfill(3),
                         taxpayer_name_padded))
            _log.info('BANK LINE FIELD Address type      (length %s [002]): %s'
                      % (str(len(taxpayer_address_type)).zfill(3),
                         taxpayer_address_type))
            _log.info('BANK LINE FIELD Street type       (length %s [002]): %s'
                      % (str(len(taxpayer_address_street_type)).zfill(3),
                         taxpayer_address_street_type))
            _log.info('BANK LINE FIELD Street name       (length %s [020]): %s'
                      % (str(len(taxpayer_address_street_name)).zfill(3),
                         taxpayer_address_street_name))
            _log.info('BANK LINE FIELD Street number     (length %s [005]): %s'
                      % (str(len(taxpayer_address_street_number)).zfill(3),
                         taxpayer_address_street_number))
            _log.info('BANK LINE FIELD Street descrip    (length %s [007]): %s'
                      % (str(len(taxpayer_address_street_description)
                             ).zfill(3),
                         taxpayer_address_street_description))
            _log.info('BANK LINE FIELD County code       (length %s [003]): %s'
                      % (str(len(county_code)).zfill(3), county_code))
            _log.info('BANK LINE FIELD County INE code   (length %s [003]): %s'
                      % (str(len(county_ine_code)).zfill(3), county_ine_code))
            _log.info('BANK LINE FIELD Province INE code (length %s [002]): %s'
                      % (str(len(province_ine_code)).zfill(3),
                         province_ine_code))
            _log.info('BANK LINE FIELD Blank space 1     (length %s [019]): %s'
                      % (str(len(blank_space1)).zfill(3), blank_space1))
            _log.info('BANK LINE FIELD Amount            (length %s [010]): %s'
                      % (str(len(amount)).zfill(3), amount))
            _log.info('BANK LINE FIELD Taxpayer VAT      (length %s [010]): %s'
                      % (str(len(taxpayer_vat)).zfill(3), taxpayer_vat))
            _log.info('BANK LINE FIELD Value format type (length %s [001]): %s'
                      % (str(len(value_format_type)).zfill(3),
                         value_format_type))
            _log.info('BANK LINE FIELD Tax_object        (length %s [040]): %s'
                      % (str(len(tax_object)).zfill(3), tax_object))
            _log.info('BANK LINE FIELD Fixed number      (length %s [012]): %s'
                      % (str(len(fixed_number)).zfill(3), fixed_number))
            _log.info('BANK LINE FIELD Fiscal year       (length %s [004]): %s'
                      % (str(len(fiscal_year)).zfill(3), fiscal_year))
            _log.info('BANK LINE FIELD Periodicity       (length %s [001]): %s'
                      % (str(len(periodicity)).zfill(3), periodicity))
            _log.info('BANK LINE FIELD Initial period    (length %s [002]): %s'
                      % (str(len(initial_period)).zfill(3), initial_period))
            _log.info('BANK LINE FIELD Final period      (length %s [002]): %s'
                      % (str(len(final_period)).zfill(3), final_period))
            _log.info('BANK LINE FIELD Line detail 1     (length %s [075]): %s'
                      % (str(len(line_detail_1)).zfill(3), line_detail_1))
            _log.info('BANK LINE FIELD Line detail 2     (length %s [075]): %s'
                      % (str(len(line_detail_2)).zfill(3), line_detail_2))
            _log.info('BANK LINE FIELD Line detail 3     (length %s [075]): %s'
                      % (str(len(line_detail_3)).zfill(3), line_detail_3))
            _log.info('BANK LINE FIELD Line detail 4     (length %s [075]): %s'
                      % (str(len(line_detail_4)).zfill(3), line_detail_4))
            _log.info('BANK LINE FIELD Blank_space 2     (length %s [100]): %s'
                      % (str(len(blank_space2)).zfill(3), blank_space2))

            # Construct bank line
            bank_line = charge_type + charge_year + \
                alicante_province_ine_code + \
                entity_code + concept_code + charge_issuance + \
                entity_type_code + value_type + entry_num_padded + \
                internal_ref + taxpayer_type + taxpayer_name_padded + \
                taxpayer_address_type + taxpayer_address_street_type + \
                taxpayer_address_street_name + \
                taxpayer_address_street_number + \
                taxpayer_address_street_description + county_code + \
                county_ine_code + province_ine_code + blank_space1 + \
                amount + taxpayer_vat + value_format_type + tax_object + \
                fixed_number + fiscal_year + periodicity + initial_period \
                + final_period + line_detail_1 + line_detail_2 + \
                line_detail_3 + line_detail_4 + blank_space2 + '\r\n'

            _log.info('FULL BANK LINE                    (length %s [643]): %s'
                      % (str(len(bank_line)).zfill(3), bank_line))

            # Add to bank_lines
            bank_lines += bank_line

            # Set as done and add suma ref
            line.write({
                'suma_ref': internal_ref,
                'suma_sent': True,
                })

        # Set total amout for SUMA resume
        # @INFO: Derived from the exact cents written to the file so the
        #        Delivery Document total equals the sum of positions 162-171.
        self.suma_total_amount = total_amount_cents / 100.0

        # Fill error tab
        if self.error_mode == 'permissive':
            self.errors_found = \
                _("Errors in payment file ") + "[" + str(error_num) \
                + " errors]\n" + errors

        # Send to the file and encode
        payment_file_str = bank_lines.encode(
            self.ENCODING_NAME, self.ENCODING_TYPE)

        # Generate filename
        filename = "SUMA_" + self.name + '_' + \
            datetime.today().strftime("%Y%m%d") + ".txt"

        # Set suma_filename for SUMA resume
        self.suma_filename = filename

        return payment_file_str, filename

    # Hooks (defaults)
    def get_entity_type_code(self):
        if self.entity_type_code:
            entity_type_code = self.entity_type_code
        else:
            raise ValidationError(_("Entity type code not set"))
        return entity_type_code

    def get_fixed_number(self, partner):
        fixed_number = str(partner.id).ljust(12)
        return fixed_number

    def create_details_lines(self, description, line, invoice):
        # Detail line 1 - Position [244-318] Length 75
        # @INFO: It is filled with payment order description
        if description:
            line_detail_1 = description[:75].ljust(75)
        else:
            line_detail_1 = str(" " * 75)
        # Detail line 2 - Position [319-393] Length 75
        # @INFO: invoice number and total amount
        # Detail line 3 - Position [394-468] Length 75
        # @INFO: surface and surface unit
        for l in line.payment_line_ids:
            if line.name == l.bank_line_id.name:
                try:
                    invoice = l.invoice_id
                except Exception:
                    invoice = False
        # Detail line 2
        if invoice:
            num = invoice.number
            # qty = invoice.quantity (invoice.line)
            invoice_amount = invoice.residual
            line_detail_2 = _("Invoice num: ") + num + ' ' + \
                _("Amount: ") + str(invoice_amount) + ' ' + \
                invoice.currency_id.name
            line_detail_2 = line_detail_2[:75].ljust(75)
            # Detail line 3
            quantity = 0.0
            if invoice.invoice_line_ids:
                unit = \
                    invoice.invoice_line_ids[0].uom_id.display_name or ""
                for invoice_line in invoice.invoice_line_ids:
                    if invoice_line.quantity:
                        quantity += invoice_line.quantity
                line_detail_3 = _("Surface: ") + str(quantity) + ' ' + unit
                line_detail_3 = line_detail_3[:75].ljust(75)
        else:
            line_detail_2 = str(" " * 75)
            line_detail_3 = str(" " * 75)
        # Detail line 4 - Position [469-543] Length 75
        line_detail_4 = str(" " * 75)
        return line_detail_1, line_detail_2, line_detail_3, line_detail_4

    # Generate direct debit file
    @api.multi
    def generate_direct_debit_file(self):
        _log = logging.getLogger(self.__class__.__name__)

        # Declare error vars
        self.errors_found = ""
        errors = ""
        error_num = 0

        # Static fields
        # Province code - Position [081-082] Length 2
        # @INFO: It's always the same 03=Alicante
        alicante_province_ine_code = "03"

        # Entity code - Positions [083-085] Length 3
        if self.entity == 'Unconfigured':
            raise ValidationError(
                _("The entity has not been configured. Set it in "
                  "Accounting/Settings."))
        else:
            entity_code = self.env['ir.values'].get_default(
                'account.config.settings', 'entity_code')

        # Charge concept code - Positions [086-087] Length 2
        concept_code = self.concept

        # Charge_issuance - Positions [088-089] Length 2
        charge_issuance = str(self.charge_issuance)

        # Reset variables
        db_lines = ""
        entry_num = 0

        # Iterate over bank lines (dynamic fields)
        for line in self.bank_line_ids:

            # Get notified to SUMA
            suma_notified = line.partner_bank_id.suma_notified

            # Value number - Position [090-095] Length 6
            # @INFO: It must contain the receipt reference within the register
            #        There cannot be repeated numbers within the same register
            #        It must always be informed
            #        It cannot be all zeros
            entry_num += 1
            entry_num_padded = str(entry_num).zfill(6)

            # Construct CCC from IBAN
            # @INFO: Format  EEEE OOOO DD NNNNNNNNNN
            #        We only add the bank account number if move.line of
            #        associated account.payment.line has as payment mode equals
            #        to Domiciliacion. The account number is the number of the
            #        mandate_id associated to it.
            for l in line.payment_line_ids:
                moveline_mandate_id = ""
                try:
                    if line.name == l.bank_line_id.name \
                            and l.move_line_id.mandate_id \
                            and l.move_line_id.payment_mode_id:
                        payment_mode = \
                            l.move_line_id.payment_mode_id.name
                        if 'bancaria' in payment_mode:
                            iban = \
                                l.mandate_id.partner_bank_id.sanitized_acc_number
                            bic = l.mandate_id.partner_bank_id.bank_bic
                            moveline_mandate_id = l.move_line_id.mandate_id
                except:
                    bic = ""
                    moveline_mandate_id = ""
                    iban = ""

            if moveline_mandate_id:
                if iban and len(iban) != 0:
                    try:
                        bic = line.mandate_id.partner_bank_id.bank_bic
                    except:
                        bic = ""

                    # Add SUMA notified
                    if suma_notified:
                        suma_notified_marker = "-Y]"
                    else:
                        suma_notified_marker = "-N]"

                    # Bank entity code - Position [001-004] Length 4
                    ccc_bank_entity_code = str(iban[4:8])
                    # Bank office code - Position [005-008] Length 4
                    ccc_bank_office_code = str(iban[8:12])
                    # Bank control digits - Position [009-010] Length 2
                    ccc_control_digits = str(iban[12:14])
                    # Bank account number - Position [011-020]Length 10
                    ccc_account_num = str(iban[14:]).ljust(10)

                else:
                    ccc_bank_entity_code = str(' ' * 4)
                    ccc_bank_office_code = str(' ' * 4)
                    ccc_control_digits = str(' ' * 2)
                    ccc_account_num = str(' ' * 10)
            else:
                continue

            # Taxpayer name - Position [021-080] Length 60
            # @INFO: lastname1 lastname2 firstname
            if line.partner_id.company_type == 'company':
                # @INFO: delete points and replace commas by spaces
                #        Limit and justify to 60 chars
                taxpayer_name = \
                    line.partner_id.name.replace(".",
                                                 "").replace(",", " ")[:60]
                taxpayer_name_padded = taxpayer_name.ljust(60)
            elif line.partner_id.company_type == 'person':
                # @INFO: partner_second_lastname dependence
                if line.partner_id.lastname:
                    taxpayer_name = line.partner_id.lastname
                    if line.partner_id.lastname2:
                        taxpayer_name += ' ' + line.partner_id.lastname2
                else:
                    if self.error_mode == 'permissive':
                        error_num += 1
                        errors += '[' + str(error_num).zfill(4) + '] ' + \
                            _("The entry number %s has failed, the lastname "
                              "for partner %s not found." %
                              (entry_num_padded, line.partner_id.name)) + '\n'
                        taxpayer_name = ""
                    else:
                        raise ValidationError(
                            _("The entry number %s has failed, the lastname "
                              "for partner %s not found." %
                              (entry_num_padded, line.partner_id.name)))
                if line.partner_id.firstname:
                    taxpayer_name += ' ' + line.partner_id.firstname
                else:
                    if self.error_mode == 'permissive':
                        error_num += 1
                        errors += '[' + str(error_num).zfill(4) + '] ' + \
                            _("The entry number %s has failed, the firstname "
                              "for partner %s not found." %
                              (entry_num_padded, line.partner_id.name)) + '\n'
                        taxpayer_name = ""
                    else:
                        raise ValidationError(
                            _("The entry number %s has failed, the firstname "
                              "for partner %s not found." %
                              (entry_num_padded, line.partner_id.name)))
                taxpayer_name_padded = taxpayer_name.ljust(60)
            else:
                if self.error_mode == 'permissive':
                    error_num += 1
                    errors += '[' + str(error_num).zfill(4) + '] ' + \
                        _("The entry number %s has failed, "
                          "taxpayer name not found." % (entry_num_padded)) + \
                        '\n'
                    taxpayer_name_padded = str(" " * 60)
                else:
                    raise ValidationError(
                        _("The entry number %s has failed, "
                          "taxpayer name not found." % (entry_num_padded)))

            # Province code       - Position [081-082] Length 2 (static)
            # Entity code         - Position [083-084] Length 2 (static)
            # Charge concept code - Position [086-087] Length 2 (static)
            # Charge_issuance     - Position [088-089] Length 2 (static)
            # Value number        - Position [090-095] Length 6 in the loop

            # Internal ref - Position [096-110] Length 15
            # @INFO: It's suma_ref in bank_line
            #        It can be empty
            if line.suma_ref:
                internal_ref = line.suma_ref
            else:
                if self.error_mode == 'permissive':
                    error_num += 1
                    errors += '[' + str(error_num).zfill(4) + '] ' + \
                        _("The entry number %s has failed, suma reference not "
                          "found." % (entry_num_padded)) + '\n'
                    internal_ref = str(" " * 15)
                else:
                    raise ValidationError(
                        _("The entry number %s has failed, suma reference not "
                          "found." % (entry_num_padded)))

            # IBAN
            # Position [111-144] Length 34
            if iban:
                iban_num = str(iban).ljust(34)
            else:
                iban_num = str(' ' * 34)

            # BIC
            # Position [145-156] Length 11
            # @INFO: mandatory if not spanish bank account
            if not iban.startswith('ES') and not bic:
                if self.error_mode == 'permissive':
                    error_num += 1
                    errors += '[' + str(error_num).zfill(4) + '] ' + \
                        _("The entry number %s has failed, bank BIC not "
                          "found. For foreign IBANs the BIC is mandatory." %
                          (entry_num_padded)) + '\n'
                else:
                    raise ValidationError(
                        _("The entry number %s has failed, bank BIC not "
                          "found. For foreign IBANs the BIC is mandatory." %
                          (entry_num_padded)))
            else:
                if bic:
                    iban_bic = str(bic).ljust(11)
                else:
                    iban_bic = str(' ' * 11)

            # Log direct debit line fields with length [and expected length]
            _log.info('NEW DB LINE. Number %s ###########################'
                      % str(entry_num).zfill(5))
            _log.info('DB LINE FIELD Bank entity code    (length %s [004]): %s'
                      % (str(len(ccc_bank_entity_code)).zfill(3),
                         ccc_bank_entity_code))
            _log.info('DB LINE FIELD Bank office code    (length %s [004]): %s'
                      % (str(len(ccc_bank_office_code)).zfill(3),
                         ccc_bank_office_code))
            _log.info('DB LINE FIELD Bank control digits (length %s [002]): %s'
                      % (str(len(ccc_control_digits)).zfill(3),
                         ccc_control_digits))
            _log.info('DB LINE FIELD Bank account num.   (length %s [010]): %s'
                      % (str(len(ccc_account_num)).zfill(3), ccc_account_num))
            _log.info('DB LINE FIELD Taxpayer name       (length %s [060]): %s'
                      % (str(len(taxpayer_name_padded)).zfill(3),
                         taxpayer_name_padded))
            _log.info('DB LINE FIELD Province INE code   (length %s [002]): %s'
                      % (str(len(alicante_province_ine_code)).zfill(3),
                         alicante_province_ine_code))
            _log.info('DB LINE FIELD Entity code         (length %s [003]): %s'
                      % (str(len(entity_code)).zfill(3), entity_code))
            _log.info('DB LINE FIELD Concept code        (length %s [002]): %s'
                      % (str(len(concept_code)).zfill(3), concept_code))
            _log.info('DB LINE FIELD Charge issuance     (length %s [002]): %s'
                      % (str(len(charge_issuance)).zfill(3), charge_issuance))
            _log.info('DB LINE FIELD Entry number        (length %s [006]): %s'
                      % (str(len(entry_num_padded)).zfill(3),
                         entry_num_padded))
            _log.info('DB LINE FIELD Internal ref        (length %s [015]): %s'
                      % (str(len(internal_ref)).zfill(3), internal_ref))
            _log.info('DB LINE FIELD Iban                (length %s [034]): %s'
                      % (str(len(iban_num)).zfill(3), iban_num))
            _log.info('DB LINE FIELD Bic                 (length %s [011]): %s'
                      % (str(len(iban_bic)).zfill(3), iban_bic))

            # Construct direct debit line
            db_line = ccc_bank_entity_code + ccc_bank_office_code + \
                ccc_control_digits + ccc_account_num + taxpayer_name_padded + \
                alicante_province_ine_code + entity_code + concept_code + \
                charge_issuance + entry_num_padded + internal_ref + \
                iban_num + iban_bic

            _log.info('FULL DB LINE                      (length %s [156]): %s'
                      % (str(len(db_line)).zfill(3), db_line))

            # Add notified marker and account_partner_bank_id to bank line
            db_line += '[' + str(line.partner_bank_id.id) + \
                suma_notified_marker + '\n'

            # Add line to db_lines
            db_lines += db_line

        # Delete lines already notified to SUMA and set suma_notified
        partner_bank_ids = []
        db_lines_to_keep = ""
        for db_line in db_lines.splitlines():
            if db_line.endswith('-N]'):
                partner_bank_id = int(db_line.split('[')[-1].split('-')[0])
                partner_bank_ids.append(partner_bank_id)
                db_line_to_keep = db_line.split('[')[0].rstrip() + '\r\n'
                db_lines_to_keep += db_line_to_keep
                _log.info(
                    'DB LINE TO KEEP                    (length %s [156]): %s'
                    % (str(len(db_line_to_keep)).zfill(3), db_line_to_keep))

        # Set suma_notified to partner_bank_ids or warn if none
        if partner_bank_ids:
            self.env['res.partner.bank'].browse(partner_bank_ids).write({
                'suma_notified': True
            })
        else:
            raise ValidationError(
                _("All the bank lines have been previously notified to SUMA."))

        # Add db_lines to file and encode
        direct_debit_str = db_lines_to_keep.encode(
            self.ENCODING_NAME, self.ENCODING_TYPE)

        # Fill error tab
        if self.error_mode == 'permissive':
            self.errors_found = \
                _("Errors in direct debit file ") + "[" + str(error_num) \
                + " errors]\n" + errors

        # Filename with associate suma payment filename
        filename = "DB_" + self.suma_filename[:-4] + ".txt"

        return direct_debit_str, filename

    @api.multi
    def print_direct_debit_file(self):
        self.ensure_one()

        direct_debit_str, filename = self.generate_direct_debit_file()
        action = {}
        if direct_debit_str and filename:
            attachment = self.env['ir.attachment'].create({
                'res_model': 'account.payment.order',
                'res_id': self.id,
                'name': filename,
                'datas': direct_debit_str.encode('base64'),
                'datas_fname': filename,
                })
            simplified_form_view = self.env.ref(
                'account_payment_order.view_attachment_simplified_form')
            action = {
                'name': _('Direct Debit File'),
                'view_mode': 'form',
                'view_id': simplified_form_view.id,
                'res_model': 'ir.attachment',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_id': attachment.id,
                }
        self.write({
            'date_generated': fields.Date.context_today(self),
            'state': 'generated',
            'generated_user_id': self._uid,
            })
        return action

    # This method is replicated by wua_account_banking_debit_suma
    @api.multi
    def generated2uploaded(self):
        res = super(AccountPaymentOrder, self).generated2uploaded()
        for order in self:
            if order.payment_mode_id.name == 'SUMA':
                for bline in order.bank_line_ids:
                    if bline.suma_sent:
                        for l in bline.payment_line_ids:
                            if bline.name == l.bank_line_id.name:
                                invoice = l.invoice_id
                                invoice.write({
                                    'in_suma': True,
                                    'suma_ref': bline.suma_ref,
                                })
        return res

    @api.multi
    def action_done_cancel(self):
        for order in self:
            if order.payment_mode_id.name == 'SUMA':
                for bline in order.bank_line_ids:
                    for l in bline.payment_line_ids:
                        if bline.name == l.bank_line_id.name:
                            invoice = l.invoice_id
                            invoice.write({
                                'in_suma': False,
                                'suma_ref': False,
                                })
        return super(AccountPaymentOrder, self).action_done_cancel()
