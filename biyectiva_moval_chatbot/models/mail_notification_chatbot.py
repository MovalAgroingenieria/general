# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MailNotificationChatbot(models.Model):
    _name = "mail.notification.chatbot"
    _description = "Chatbot Mail Notification Snapshot"
    _auto = False
    _rec_name = "task_name"
    _order = "id DESC"
    _table = "mail_notification_chatbot_mv"

    id = fields.Integer(string="Notification ID")
    author_id = fields.Many2one("res.partner", string="Notification Author")
    author_name = fields.Char(string="Author Name")
    is_read = fields.Boolean(string="Is Read")
    res_partner_id = fields.Many2one("res.partner", string="Recipient")
    res_partner_name = fields.Char(string="Recipient Name")
    mail_message_id = fields.Many2one("mail.message", string="Mail Message")
    message_body = fields.Html(string="Message Body")
    message_model = fields.Char(string="Message Model")
    message_res_id = fields.Integer(string="Related Record ID")
    message_res_name = fields.Char(string="Related Record Name")
    message_subtype_id = fields.Many2one(
        "mail.message.subtype", string="Message Subtype"
    )
    message_subtype_name = fields.Char(string="Subtype Name")
    message_type = fields.Char(string="Message Type")
    message_type_label = fields.Char(string="Message Type Label")
    task_name = fields.Char(string="Task")
    task_stage_id = fields.Many2one("project.task.type", string="Stage")
    task_stage_name = fields.Char(string="Stage Name")
    task_project_id = fields.Many2one("project.project", string="Project")
    task_project_name = fields.Char(string="Project Name")
    task_user_names = fields.Char(string="Assignees")
    task_reviewer_id = fields.Many2one("res.users", string="Reviewer")
    task_reviewer_name = fields.Char(string="Reviewer Name")
    task_partner_id = fields.Many2one("res.partner", string="Customer")
    task_partner_name = fields.Char(string="Customer Name")
    task_tag_names = fields.Char(string="Tags")
    task_date_deadline = fields.Date(string="Date Deadline")
    task_recurring = fields.Boolean(string="Recurring Task")
    task_type_id = fields.Many2one("project.type", string="Task Type")
    task_type_name = fields.Char(string="Task Type Name")
    write_date = fields.Datetime(string="Last Modified on")
    # Security fields for efficient filtering
    project_privacy_visibility = fields.Selection(
        [
            ("followers", "Invited internal users"),
            ("employees", "All internal users"),
            ("portal", "Invited portal users and all internal users"),
        ],
        string="Project Visibility",
    )
    project_company_id = fields.Many2one(
        "res.company", string="Project Company"
    )

    timesheet_last_date = fields.Date(string="Last Timesheet Date")
    timesheet_last_user_id = fields.Many2one(
        "res.users", string="Last Timesheet User"
    )
    timesheet_last_user_name = fields.Char(string="Last Timesheet User Name")
    timesheet_total_hours = fields.Float(string="Total Hours")
    timesheet_last_description = fields.Char(
        string="Last Timesheet Description"
    )

    def init(self):
        self._drop_materialized_view()
        self._create_materialized_view()
        self._create_indexes()

    def _drop_materialized_view(self):
        self.env.cr.execute(
            f"DROP MATERIALIZED VIEW IF EXISTS {self._table} CASCADE"
        )

    def _create_materialized_view(self):
        self.env.cr.execute(
            f"""
            CREATE MATERIALIZED VIEW {self._table} AS
            WITH user_aggregates AS (
                SELECT
                    r.task_id,
                    string_agg(
                        COALESCE(p.name, u.login),
                        ', '
                        ORDER BY COALESCE(p.name, u.login)
                    ) AS user_names
                FROM project_task_user_rel r
                JOIN res_users u ON u.id = r.user_id
                LEFT JOIN res_partner p ON p.id = u.partner_id
                GROUP BY r.task_id
            ),
            tag_aggregates AS (
                SELECT
                    r.project_task_id,
                    string_agg(
                        t.name::text,
                        ', '
                        ORDER BY t.name::text
                    ) AS tag_names
                FROM project_tags_project_task_rel r
                JOIN project_tags t ON t.id = r.project_tags_id
                GROUP BY r.project_task_id
            ),
            timesheet_aggregates AS (
                SELECT
                    task_id,
                    SUM(unit_amount) as total_hours,
                    MAX(date) as last_date
                FROM account_analytic_line
                WHERE task_id IS NOT NULL
                GROUP BY task_id
            ),
            timesheet_last_details AS (
                SELECT DISTINCT ON (task_id)
                    task_id,
                    user_id,
                    name
                FROM account_analytic_line
                WHERE task_id IS NOT NULL
                ORDER BY task_id, date DESC, id DESC
            )
            SELECT
                notif.id,
                msg.write_date AS write_date,
                notif.author_id,
                COALESCE(author.name, '') AS author_name,
                notif.is_read,
                notif.res_partner_id,
                COALESCE(recipient.name, '') AS res_partner_name,
                notif.mail_message_id,
                COALESCE(msg.body, '') AS message_body,
                msg.model AS message_model,
                msg.res_id::bigint AS message_res_id,
                COALESCE(task.name::text, '') AS message_res_name,
                msg.subtype_id AS message_subtype_id,
                COALESCE(subtype.name::text, '') AS message_subtype_name,
                msg.message_type,
                CASE msg.message_type
                    WHEN 'email' THEN 'Correo electrónico'
                    WHEN 'comment' THEN 'Comentario'
                    ELSE COALESCE(msg.message_type, '')
                END AS message_type_label,
                COALESCE(task.name::text, '') AS task_name,
                task.stage_id AS task_stage_id,
                COALESCE(stage.name::text, '') AS task_stage_name,
                task.project_id AS task_project_id,
                COALESCE(project.name::text, '') AS task_project_name,
                task.reviewer_id AS task_reviewer_id,
                COALESCE(reviewer_partner.name, '') AS task_reviewer_name,
                task.partner_id AS task_partner_id,
                COALESCE(partner.name, '') AS task_partner_name,
                task.date_deadline AS task_date_deadline,
                COALESCE(task.recurring_task, FALSE) AS task_recurring,
                task.type_id AS task_type_id,
                COALESCE(task_type.name::text, '') AS task_type_name,
                COALESCE(ua.user_names, '') AS task_user_names,
                COALESCE(ta.tag_names, '') AS task_tag_names,
                ts_agg.last_date AS timesheet_last_date,
                ts_agg.total_hours AS timesheet_total_hours,
                ts_last.user_id AS timesheet_last_user_id,
                COALESCE(
                    ts_user_partner.name, ts_user.login
                ) AS timesheet_last_user_name,
                COALESCE(ts_last.name, '') AS timesheet_last_description,
                -- Security fields for efficient filtering
                project.privacy_visibility AS project_privacy_visibility,
                project.company_id AS project_company_id
            FROM mail_notification notif
            INNER JOIN mail_message msg
                ON msg.id = notif.mail_message_id
                AND msg.model = 'project.task'
                AND msg.message_type IN ('comment', 'email')
            INNER JOIN project_task task ON task.id = msg.res_id
            LEFT JOIN res_partner author ON author.id = notif.author_id
            LEFT JOIN res_partner recipient
                ON recipient.id = notif.res_partner_id
            LEFT JOIN mail_message_subtype subtype
                ON subtype.id = msg.subtype_id
            LEFT JOIN project_task_type stage ON stage.id = task.stage_id
            LEFT JOIN project_project project ON project.id = task.project_id
            LEFT JOIN res_users reviewer ON reviewer.id = task.reviewer_id
            LEFT JOIN res_partner reviewer_partner
                ON reviewer_partner.id = reviewer.partner_id
            LEFT JOIN res_partner partner ON partner.id = task.partner_id
            LEFT JOIN project_type task_type ON task_type.id = task.type_id
            LEFT JOIN user_aggregates ua ON ua.task_id = task.id
            LEFT JOIN tag_aggregates ta ON ta.project_task_id = task.id
            LEFT JOIN timesheet_aggregates ts_agg ON ts_agg.task_id = task.id
            LEFT JOIN timesheet_last_details ts_last
                ON ts_last.task_id = task.id
            LEFT JOIN res_users ts_user ON ts_user.id = ts_last.user_id
            LEFT JOIN res_partner ts_user_partner
                ON ts_user_partner.id = ts_user.partner_id
        """
        )

    def _create_indexes(self):
        statements = (
            (
                f"CREATE UNIQUE INDEX IF NOT EXISTS {self._table}_id_uidx "
                f"ON {self._table} (id)"
            ),
            (
                f"CREATE INDEX IF NOT EXISTS {self._table}_recipient_idx "
                f"ON {self._table} (res_partner_id)"
            ),
            (
                f"CREATE INDEX IF NOT EXISTS {self._table}_message_idx "
                f"ON {self._table} (mail_message_id)"
            ),
            (
                f"CREATE INDEX IF NOT EXISTS {self._table}_project_idx "
                f"ON {self._table} (task_project_id)"
            ),
            (
                f"CREATE INDEX IF NOT EXISTS {self._table}_stage_idx "
                f"ON {self._table} (task_stage_id)"
            ),
            (
                f"CREATE INDEX IF NOT EXISTS {self._table}_deadline_idx "
                f"ON {self._table} (task_date_deadline)"
            ),
            (
                f"CREATE INDEX IF NOT EXISTS {self._table}_is_read_idx "
                f"ON {self._table} (is_read)"
            ),
            # Security-related indexes for _search filtering
            (
                f"CREATE INDEX IF NOT EXISTS {self._table}_privacy_idx "
                f"ON {self._table} (project_privacy_visibility)"
            ),
            (
                f"CREATE INDEX IF NOT EXISTS {self._table}_company_idx "
                f"ON {self._table} (project_company_id)"
            ),
            (
                f"CREATE INDEX IF NOT EXISTS "
                f"{self._table}_security_combined_idx "
                f"ON {self._table} "
                "(project_privacy_visibility, task_project_id, "
                "message_res_id)"
            ),
            # mail_followers index for security checks
            (
                "CREATE INDEX IF NOT EXISTS "
                "idx_mail_followers_security "
                "ON mail_followers (partner_id, res_model, res_id)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS "
                "idx_mail_message_task_filter "
                "ON mail_message (model, message_type, res_id) "
                "WHERE model = 'project.task' "
                "AND message_type IN ('comment', 'email')"
            ),
            (
                "CREATE INDEX IF NOT EXISTS "
                "idx_task_user_rel_task_inc "
                "ON project_task_user_rel (task_id) "
                "INCLUDE (user_id)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS "
                "idx_task_tags_rel_task_inc "
                "ON project_tags_project_task_rel (project_task_id) "
                "INCLUDE (project_tags_id)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS "
                "idx_mail_notification_message_inc "
                "ON mail_notification (mail_message_id) "
                "INCLUDE (author_id, res_partner_id, is_read)"
            ),
        )
        for statement in statements:
            self.env.cr.execute(statement)

        gin_statement = (
            f"CREATE INDEX IF NOT EXISTS {self._table}_body_gin_idx "
            f"ON {self._table} USING gin("
            f"to_tsvector('spanish', LEFT(message_body, 500000)))"
        )
        try:
            self.env.cr.execute(gin_statement)
        except Exception:
            pass

    @api.model
    def _search(
        self,
        args,
        offset=0,
        limit=None,
        order=None,
        count=False,
        access_rights_uid=None,
    ):
        """Override _search to apply mail.message security.

        A user can see a notification if they can see the associated
        mail.message. This delegates security to the mail.message model
        which already has proper ir.rules that check access to the
        parent record (project.task in this case).
        """
        # Get base IDs first (applies any domain from args)
        base_query = super()._search(
            args,
            offset=0,
            limit=None,
            order=order,
            count=False,
            access_rights_uid=access_rights_uid,
        )

        # If superuser, skip security filtering
        user = self.env.user
        if user._is_superuser():
            if count:
                return len(base_query)
            base_ids = list(base_query)
            end_idx = offset + limit if limit else None
            return self.browse(base_ids[offset:end_idx])

        # Handle empty results
        base_ids = list(base_query)
        if not base_ids:
            return 0 if count else self.browse()

        # Get the mail_message_ids from the notifications
        self.env.cr.execute(
            """
            SELECT id, mail_message_id
            FROM mail_notification_chatbot_mv
            WHERE id = ANY(%s)
            """,
            (base_ids,),
        )
        notif_to_msg = {r[0]: r[1] for r in self.env.cr.fetchall()}
        message_ids = list(set(notif_to_msg.values()))

        if not message_ids:
            return 0 if count else self.browse()

        # Use mail.message security to filter accessible messages
        # This leverages the existing ir.rules on mail.message
        accessible_messages = self.env["mail.message"]._search(
            [("id", "in", message_ids)]
        )
        accessible_msg_ids = set(accessible_messages)

        # Filter notifications to only those with accessible messages
        secure_ids = [
            notif_id
            for notif_id in base_ids
            if notif_to_msg.get(notif_id) in accessible_msg_ids
        ]

        if count:
            return len(secure_ids)

        # Apply offset and limit
        end_idx = offset + limit if limit else None
        final_ids = secure_ids[offset:end_idx]

        _logger.debug(
            "mail.notification.chatbot._search: "
            "base=%d, messages=%d, accessible=%d, secure=%d, final=%d",
            len(base_ids),
            len(message_ids),
            len(accessible_msg_ids),
            len(secure_ids),
            len(final_ids),
        )
        return self.browse(final_ids)

    @api.model
    def refresh_materialized_view(self, concurrently=False):
        """Refresh the materialized view with the latest data."""
        query = "REFRESH MATERIALIZED VIEW"
        if concurrently:
            query += " CONCURRENTLY"
        query += f" {self._table}"
        self.env.cr.execute(query)
        self.env.cr.execute(f"ANALYZE {self._table}")

    @api.model
    def cron_refresh_materialized_view(self):
        import logging
        import time
        from datetime import datetime

        _logger = logging.getLogger(__name__)
        start_time = time.monotonic()
        start_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            self.sudo().refresh_materialized_view(concurrently=True)
            mode = "concurrently"
        except Exception as e:
            _logger.warning(
                "Concurrent refresh failed, falling back to standard: %s", e
            )
            self.env.cr.rollback()
            self.sudo().refresh_materialized_view(concurrently=False)
            mode = "standard"

        elapsed = time.monotonic() - start_time
        _logger.info(
            "Refreshed %s (%s) in %.3f seconds (start=%s)",
            self._table,
            mode,
            elapsed,
            start_timestamp,
        )
        return True

    def action_refresh_materialized_view(self):
        """Action to manually refresh the materialized view."""
        try:
            self.sudo().refresh_materialized_view(concurrently=True)
            message = _(
                "Materialized view refreshed successfully"
            )
        except Exception:
            self.env.cr.rollback()
            self.sudo().refresh_materialized_view(concurrently=False)
            message = _(
                "Materialized view refreshed successfully"
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": message,
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _raise_readonly(self):
        raise UserError(_("This dataset is read-only."))

    @api.model_create_multi
    def create(self, vals_list):
        self._raise_readonly()

    def write(self, vals):
        self._raise_readonly()

    def unlink(self):
        self._raise_readonly()
