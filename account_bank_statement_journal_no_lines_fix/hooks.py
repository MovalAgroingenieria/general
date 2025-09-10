# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """
    Post-installation hook to recompute validation for all bank statements
    without lines.
    """
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    # Find all bank statements without lines
    statements_without_lines = env['account.bank.statement'].search([
        ('line_ids', '=', False)
    ])

    if statements_without_lines:
        _logger.info(
            "Recomputing validation for %d bank statements without lines",
            len(statements_without_lines)
        )

        # Group by journal and process in chronological order
        journals = statements_without_lines.mapped('journal_id')
        for journal in journals:
            journal_statements = statements_without_lines.filtered(
                lambda s: s.journal_id == journal
            ).sorted(lambda s: (s.date, s.id))

            # Force recomputation of is_complete field for this journal
            journal_statements._compute_is_complete()

            _logger.info(
                "Recomputed %d statements for journal %s",
                len(journal_statements), journal.name
            )

        _logger.info(
            "Validation recomputation completed for bank statements "
            "without lines"
        )
    else:
        _logger.info("No bank statements without lines found")


def uninstall_hook(cr, registry):
    """
    Uninstallation hook to clean up any custom data if needed.
    """
    _logger.info("Account Bank Statement Journal Fix module uninstalled")
