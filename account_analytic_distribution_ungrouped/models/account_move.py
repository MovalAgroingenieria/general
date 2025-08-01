# 2023 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Campo many2one para una sola cuenta analítica
    analytic_account_single = fields.Many2one(
        'account.analytic.account',
        string='Cuenta Analítica',
        compute='_compute_analytic_account_single',
        inverse='_inverse_analytic_account_single',
        store=False,
        help='Selecciona una cuenta analítica (se asignará automáticamente '
             'el 100%)'
    )

    @api.depends('analytic_distribution')
    def _compute_analytic_account_single(self):
        """Convertir el JSON analytic_distribution a un campo many2one"""
        for line in self:
            if line.analytic_distribution:
                # Tomar la primera cuenta del JSON (solo manejamos una)
                account_ids = list(line.analytic_distribution.keys())
                if account_ids:
                    line.analytic_account_single = int(account_ids[0])
                else:
                    line.analytic_account_single = False
            else:
                line.analytic_account_single = False

    def _inverse_analytic_account_single(self):
        """Convertir el campo many2one de vuelta a JSON
        analytic_distribution"""
        for line in self:
            if line.analytic_account_single:
                # Asignar 100% a la cuenta seleccionada
                line.analytic_distribution = {
                    str(line.analytic_account_single.id): 100.0
                }
            else:
                line.analytic_distribution = {}
