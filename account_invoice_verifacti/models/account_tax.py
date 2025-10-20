# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class AccountTax(models.Model):
    """Tax extension for Verifacti"""

    _inherit = 'account.tax'

    verifacti_tax_type = fields.Selection([
            ('01', 'VAT'),
            ('02', 'IGIC'),
            ('03', 'IPSI'),
            ('04', 'Other')
        ],
        string='Verifacti Tax Type',
        default='01',
        help='Tax type for Verifacti: 01=VAT, 02=IGIC (Canary Islands), 03=IPSI (Ceuta and Melilla)',
    )

    verifacti_operation_classification = fields.Selection([
            ('S1', 'S1 - General regime operation'),
            ('S2', 'S2 - Operation under special regime or reverse charge application'),
            ('N1', 'N1 - Non-subject operation'),
            ('N2', 'N2 - Non-subject operation by location rules')
        ],
        string='Operation Classification',
        default='S1',
        help='Operation classification according to Verifacti',
    )

    verifacti_regime_code = fields.Selection([
            ('01', '01 - General regime'),
            ('02', '02 - Export regime'),
            ('03', '03 - Special regime for used goods'),
            ('04', '04 - Special regime for investment gold'),
            ('05', '05 - Special regime for travel agencies'),
            ('06', '06 - Special regime VAT group of entities (Advanced level)'),
            ('07', '07 - Special cash accounting regime'),
            ('08', '08 - Special regime for retail tobacco trade'),
            ('09', '09 - Special regime for telecommunications'),
            ('10', '10 - Special regime for electronic, broadcasting or television services'),
            ('11', '11 - Special regime for agriculture, livestock and fishing'),
            ('12', '12 - Special regime for domestic operations'),
            ('13', '13 - Special regime for delivery of works of art'),
            ('14', '14 - Special regime for equivalence surcharge'),
            ('15', '15 - Simplified special regime'),
        ],
        string='Regime Code',
        help='Special regime or significance code applicable to this tax.',
    )

    verifacti_exempt_operation = fields.Selection([
            ('E1', 'E1 - Exempt pursuant to Article 20'),
            ('E2', 'E2 - Exempt pursuant to Article 21'),
            ('E3', 'E3 - Exempt pursuant to Article 22'),
            ('E4', 'E4 - Exempt pursuant to Articles 23 and 24'),
            ('E5', 'E5 - Exempt pursuant to Article 25'),
            ('E6', 'E6 - Other exemptions'),
        ],
        string='Exempt Operation',
        help='Exemption code for exempt operations (E1-E6). When set, tax_rate and tax_amount are not required.',
    )

    verifacti_surcharge_rate = fields.Float(
        string='Surcharge Rate (%)',
        digits=(5, 2),
        default=0.0,
        help='Equivalence surcharge rate (recargo de equivalencia) applicable to this tax. For example: 0.5, 1.4, 5.2',
    )

    verifacti_is_surcharge = fields.Boolean(
        string='Is Surcharge Tax',
        default=False,
        help='Check this if this tax represents an equivalence surcharge (recargo de equivalencia) applied as a child tax.',
    )

    verifacti_cost_based_tax_base = fields.Float(
        string='Cost-Based Tax Base',
        digits=(16, 2),
        help='Tax base at cost for special regimes (06) or special taxes (02, 05). Only applicable in specific cases.',
    )
