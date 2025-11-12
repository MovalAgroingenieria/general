# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class BankinplayResponse(models.Model):
    _name = "bankinplay.response"
    _description = (
        "Intermediate table to temporarily store Bankinplay responses when "
        "this database is acting as a remote endpoint."
    )

    # Used later by callbacks to route decrypted payloads correctly
    bankinplay_signature = fields.Char(
        readonly=True,
        copy=False,
        index="btree_not_null",  # Changed from True to specific index type
        help="Signature returned by Bankinplay to authenticate the callback.",
    )

    bankinplay_responseid = fields.Char(
        string="Bankinplay Response ID",
        readonly=True,
        copy=False,
        index="btree_not_null",  # Changed from True to specific index type
        help="Response identifier returned by Bankinplay for this request.",
    )

    # Store (usually decrypted) JSON string for traceability/debugging
    bankinplay_response = fields.Text(
        readonly=True,
        copy=False,
        help="Full JSON payload that was forwarded to the client database.",
    )

    # Where to forward the callback (base URL of the client DB)
    endpoint_return_url = fields.Char(
        string="Client Database URL",
        readonly=True,
        copy=False,
        help="Base URL of the client DB that will receive "
        "/webhook/bankinplay_callback.",
    )

    _sql_constraints = [
        (
            "bankinplay_resp_sig_unique",
            "unique(bankinplay_responseid, bankinplay_signature)",
            "A stored response with this Bankinplay response/signature already exists.",
        ),
    ]

    @api.model
    def delete_old_responses(self, weeks=1, batch_size=1000):
        """Purge old transient rows to keep the table small.

        Args:
            weeks (int): Age threshold; rows older than this
            are deleted. Default 1 week.
            batch_size (int): Delete in batches to avoid long locks/PG bloat.
        """
        # Use Odoo's TZ-aware clock; create_date is UTC Datetime
        limit_date = fields.Datetime.now() - relativedelta(weeks=weeks)

        domain = [("create_date", "<", limit_date)]
        while True:
            old_batch = self.search(domain, limit=batch_size)
            if not old_batch:
                break
            # sudo() in case the cron user has limited rights
            old_batch.sudo().unlink()
        return True
