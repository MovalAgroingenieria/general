# -*- coding: utf-8 -*-
# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models, _, api
from odoo.exceptions import UserError
import time
import json
import traceback
import requests
import base64
import pytz
import pyodbc
import logging
_logger = logging.getLogger(__name__)


class RemoteControl(models.Model):
    _name = 'remotecontrol'
    _description = 'Remote Control Definition'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Name',
        required=True,
        track_visibility='onchange',
    )

    remotecontrol_type = fields.Selection(
        string='Remote Control Type',
        selection=[
            ('rest', 'REST'),
            ('sql', 'SQL'),
        ],
        required=True,
        track_visibility='onchange',
    )

    base_url = fields.Char(
        string='Base URL',
    )

    timeout = fields.Integer(
        string='Timeout',
        default=10,
    )

    verify_ssl = fields.Boolean(
        string='Verify SSL',
        default=True,
    )

    rate_limit_seconds = fields.Float(
        string='Rate Limit Seconds',
        default=0.0,
    )

    max_retries = fields.Integer(
        string='Max Retries',
        default=1,
    )

    backoff = fields.Float(
        string='Backoff',
        default=1.5,
    )

    connection_params = fields.Text(
        string='Connection Parameters',
        help='JSON-encoded connection parameters.',
    )

    action_count = fields.Integer(
        string='Actions Count',
        compute='_compute_action_count',
    )

    readonly = fields.Boolean(
        string='Read Only',
        readonly=True,
        default=False,
    )

    remotecontrol_help = fields.Html(
        string='Help',
        translate=True,
        sanitize=True,
    )

    connection_params_valid = fields.Boolean(
        string='Valid JSON Connector',
        compute='_compute_connection_params_valid',
        store=True,
    )

    @api.multi
    def _compute_action_count(self):
        for record in self:
            action_model = self.env['remotecontrol.action']
            record.action_count = action_model.search_count(
                [('remote_id', '=', record.id)])

    @api.depends('connection_params')
    def _compute_connection_params_valid(self):
        for record in self:
            connection_params_valid = True
            if record.connection_params:
                try:
                    json.loads(record.connection_params)
                    connection_params_valid = True
                except (ValueError, TypeError):
                    connection_params_valid = False
            record.connection_params_valid = connection_params_valid

    def action_view_actions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Actions'),
            'res_model': 'remotecontrol.action',
            'view_mode': 'tree,form',
            'domain': [('remote_id', '=', self.id)],
            'context': {'default_remote_id': self.id},
        }

    def action_view_procedures(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Procedures'),
            'res_model': 'remotecontrol.procedure',
            'view_mode': 'tree,form',
            'domain': [('remote_id', '=', self.id)],
            'context': {'default_remote_id': self.id},
        }

    def message_log(self, body):
        for record in self:
            try:
                record.message_post(body=body)
            except Exception as e:
                _logger.error("Error logging %s: %s", record.id, e)

    def _build_rest_client(self):
        session = requests.Session()
        session.verify = self.verify_ssl
        return session

    def request_with_retries(self, method, url, max_retries=None, backoff=None,
                             timeout=None, verify=None, **kwargs):
        max_retries = max_retries or self.max_retries or 1
        backoff = backoff or self.backoff or 1.5
        timeout = timeout or self.timeout or 10
        verify = verify if verify is not None else self.verify_ssl
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                response = requests.request(
                    method, url, timeout=timeout, verify=verify, **kwargs)
                return response
            except requests.RequestException as exception:
                last_exception = exception
                if attempt < max_retries:
                    delay = (backoff ** attempt)
                    time.sleep(delay)
                else:
                    break
        if last_exception:
            raise last_exception

    def upsert(self, model_name, key_vals, other_vals=None):
        self.ensure_one()
        Model = self.env[model_name]
        domain = [(field, '=', value) for field, value in key_vals.items()]
        rec = Model.search(domain, limit=1)
        vals = {}
        vals.update(key_vals or {})
        if other_vals:
            vals.update(other_vals)
        if rec:
            rec.write(vals)
            return rec
        else:
            return Model.create(vals)

    def _remotecontrol_sql_connect(self):
        self.ensure_one()
        if self.remotecontrol_type != 'sql':
            raise UserError(
                _("SQL connection is only available for 'sql' type remote "
                  "controls."))
        try:
            params = json.loads(self.connection_params or '{}')
        except (ValueError, TypeError):
            raise UserError(_("Invalid JSON in connection_params."))
        host = params.get('host', 'localhost')
        port = params.get('port', 1433)
        database = params.get('database', '')
        user = params.get('user', '')
        password = params.get('password', '')
        if not database or not user:
            raise UserError(
                _("Database and user are required in connection_params."))
        # Build connection string for SQL Server
        driver_name = params.get('driver_name', 'SQL Server')
        connection_string = (
            'DRIVER={%s};SERVER=%s;PORT=%s;DATABASE=%s;UID=%s;PWD=%s' % (
                driver_name, host, port, database, user, password,
            )
        )
        # Add optional parameters
        if params.get('tds_version'):
            connection_string += ';TDS_Version=%s' % params['tds_version']
        if params.get('trusted_connection'):
            connection_string += ';Trusted_Connection=yes'
        connection = pyodbc.connect(connection_string)
        # Configure pyodbc to return UTF-8 strings for SQL Server
        # (avoids encoding issues in Python 2.7 when working with CSV)
        sql_server_drivers = (
            'SQL Server', 'FreeTDS', 'ODBC Driver 17 for SQL Server',
        )
        if driver_name in sql_server_drivers:
            connection.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
            connection.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
            connection.setencoding(str, encoding='utf-8')
            connection.setencoding(unicode, encoding='utf-8')
        cursor = connection.cursor()
        return cursor

    @api.multi
    def _remotecontrol_sql_execute(self, cursor, query, params=None):
        self.ensure_one()
        if not cursor:
            raise UserError(
                _("No cursor provided. Call sql_connect() first and store "
                  "the result in bag['_sql_cursor']."))
        cursor.execute(query, params or ())
        return cursor

    @api.multi
    def _remotecontrol_sql_fetchall(self, cursor):
        self.ensure_one()
        if not cursor:
            raise UserError(
                _("No cursor provided."))
        return cursor.fetchall()

    @api.multi
    def _remotecontrol_sql_fetchone(self, cursor):
        self.ensure_one()
        if not cursor:
            raise UserError(
                _("No cursor provided."))
        return cursor.fetchone()

    @api.multi
    def _remotecontrol_sql_close(self, cursor):
        self.ensure_one()
        if cursor:
            try:
                connection = cursor.connection
                cursor.close()
                if connection:
                    connection.close()
            except Exception:
                pass

    def unlink(self):
        force_unlink = self.env.context.get('force_unlink', False)
        if (not force_unlink):
            for record in self:
                if record.readonly:
                    raise UserError(
                        _("You cannot delete a read-only Remote Control."))
        return super(RemoteControl, self).unlink()


class RemoteControlAction(models.Model):
    _name = 'remotecontrol.action'
    _description = 'Remote Control Action'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Name',
        required=True,
    )

    active = fields.Boolean(
        string='Active',
        default=True,
    )

    remote_id = fields.Many2one(
        string='Remote Control',
        comodel_name='remotecontrol',
        required=True,
        ondelete='cascade',
    )

    code = fields.Text(
        string="Python Code",
        required=True,
        help="Functional snippet. Receives variables: env, self, bag, "
             "base_url, timeout, fields, request_retry.",
    )

    rate_limit_seconds = fields.Float(
        string='Rate Limit Seconds',
        default=0.0,
        help="Extra delay before executing this action (seconds).",
    )

    max_retries = fields.Integer(
        string='Max Retries',
        default=1,
        help="Network retry attempts inside request_retry.",
    )

    backoff = fields.Float(
        string='Backoff',
        default=1.5,
        help="Exponential backoff base.",
    )

    readonly = fields.Boolean(
        string='Read Only',
        readonly=True,
        default=False,
    )

    def _prepare_action_context(self, bag=None):
        self.ensure_one()
        bag = dict(bag or {})
        remote_control = self.remote_id
        context = {
            'env': self.env,
            'self': self,
            'bag': bag,
            'base_url': remote_control.base_url or '',
            'timeout': remote_control.timeout,
            'fields': fields,
            'json': json,
            'base64': base64,
            'pytz': pytz,
            'request_retry': lambda method, url, **kwargs: (
                remote_control.request_with_retries(
                    method, url,
                    max_retries=kwargs.pop('max_retries', None),
                    backoff=kwargs.pop('backoff', None),
                    timeout=kwargs.pop('timeout', None),
                    verify=kwargs.pop('verify', None),
                    **kwargs
                )
            ),
            'upsert': lambda model_name, key_vals, other_vals=None: (
                remote_control.upsert(
                    model_name, key_vals, other_vals=other_vals,
                )
            ),
            'sql_connect': lambda: (
                remote_control._remotecontrol_sql_connect()
            ),
            'sql_execute': lambda cursor, query, params=None: (
                remote_control._remotecontrol_sql_execute(
                    cursor, query, params=params,
                )
            ),
            'sql_fetchall': lambda cursor: (
                remote_control._remotecontrol_sql_fetchall(cursor)
            ),
            'sql_fetchone': lambda cursor: (
                remote_control._remotecontrol_sql_fetchone(cursor)
            ),
            'sql_close': lambda cursor: (
                remote_control._remotecontrol_sql_close(cursor)
            ),
        }
        return context

    def execute(self, bag=None):
        self.ensure_one()
        bag = dict(bag or {})
        action_name = self.name
        remote_control = self.remote_id
        context = self._prepare_action_context(bag=bag)
        try:
            if self.rate_limit_seconds:
                time.sleep(self.rate_limit_seconds)
            exec(self.code, context)
            remote_control.message_log(
                u"[Action %s] executed successfully." % (action_name,))
        except Exception as e:
            traceback_info = traceback.format_exc()
            raise UserError(
                _("Execution error (%s) in action '%s':\n%s") % (
                    action_name, traceback_info, str(e)))
        # Return the bag from context as it may have been modified by exec
        return context.get('bag', bag)

    def test_execute(self):
        self.ensure_one()
        action_name = self.name
        remote_name = self.remote_id.name
        result_bag = {}
        try:
            with self.env.cr.savepoint():
                result_bag = self.execute(bag={})
                raise Exception("__ROLLBACK__")
        except Exception as e:
            if unicode(e) == "__ROLLBACK__":
                message = _(u"Test Successful (dry-run)\n\n")
                message += _(u"Action: %s\n") % action_name
                message += _(u"Remote Control: %s\n\n") % remote_name
                message += _(u"Results:\n")
                if result_bag:
                    for k, v in result_bag.items():
                        val = unicode(v)
                        message += u"  • %s: %s\n" % (k, val[:200])
                        if len(val) > 200:
                            message += u"...\n"
                else:
                    message += _(u"  (No data returned)\n")
                return {
                    'type': 'ir.actions.act_window.message',
                    'title': _(u'Test Successful'),
                    'message': message,
                    'is_html_message': False,
                    'close_button_title': False,
                    'buttons': [
                        {'type': 'ir.actions.act_window_close',
                         'name': _(u'Close')},
                    ],
                }
            else:
                error_message = _(u"Test Failed\n\n")
                error_message += _(u"Action: %s\n") % action_name
                error_message += _(u"Remote Control: %s\n\n") % remote_name
                error_message += _(u"Error: %s") % unicode(e)
                return {
                    'type': 'ir.actions.act_window.message',
                    'title': _(u'Test Failed'),
                    'message': error_message,
                    'is_html_message': False,
                    'close_button_title': False,
                    'buttons': [
                        {'type': 'ir.actions.act_window_close',
                         'name': _(u'Close')},
                    ],
                }

    def unlink(self):
        force_unlink = self.env.context.get('force_unlink', False)
        if (not force_unlink):
            for record in self:
                if record.readonly:
                    raise UserError(
                        _("You cannot delete a read-only Action."))
        return super(RemoteControlAction, self).unlink()


class RemoteControlProcedure(models.Model):
    _name = 'remotecontrol.procedure'
    _description = 'Remote Control Procedure'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Name',
        required=True,
    )

    active = fields.Boolean(
        string='Active',
        default=True,
    )

    remote_id = fields.Many2one(
        string='Remote Control',
        comodel_name='remotecontrol',
        required=True,
        ondelete='cascade',
    )

    step_ids = fields.One2many(
        string='Steps',
        comodel_name='remotecontrol.step',
        inverse_name='procedure_id',
    )

    cron_id = fields.Many2one(
        string='Scheduled Cron',
        comodel_name='ir.cron',
        ondelete='set null',
    )

    interval_number = fields.Integer(
        string="Interval Number",
        default=10,

    )

    interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ],
        default='minutes',
    )

    nextcall = fields.Datetime(
        string="Next Execution",
        default=fields.Datetime.now,
        related='cron_id.nextcall',
        store=True,
    )

    numbercall = fields.Integer(
        string="Number of Calls",
        default=-1,
    )

    readonly = fields.Boolean(
        string='Read Only',
        readonly=True,
        default=False,
    )

    # Hook method to prepare the initial bag for procedure execution.
    # Can be overridden by inherited modules to add custom data to the bag.
    def _prepare_procedure_bag(self, bag=None):
        return dict(bag or {})

    def run(self, procedure_id=None):
        procedures = []
        if self:
            procedures = self
        elif procedure_id:
            procedures = self.browse(procedure_id)
        for procedure in procedures:
            bag = procedure._prepare_procedure_bag()
            for step in procedure.step_ids.sorted(key=lambda s: s.sequence):
                bag = step.action_id.execute(bag=bag)
            procedure.remote_id.message_log(
                u"Procedure '%s' finished OK." % procedure.name)
        return True

    def test_run(self):
        self.ensure_one()
        procedure_name = self.name
        remote_name = self.remote_id.name
        bag = {}
        step_results = []
        try:
            with self.env.cr.savepoint():
                for step in self.step_ids.sorted(key=lambda s: s.sequence):
                    step_name = step.name or step.action_id.name
                    try:
                        bag = step.action_id.execute(bag=bag)
                        step_results.append(u"OK: %s" % step_name)
                    except Exception as e:
                        step_results.append(
                            u"FAILED: %s (%s)" % (step_name, unicode(e)))
                        raise
                raise Exception("__ROLLBACK__")
        except Exception as e:
            if unicode(e) == "__ROLLBACK__":
                message = _(u"Procedure Test Successful (dry-run)\n\n")
                message += _(u"Procedure: %s\n") % procedure_name
                message += _(u"Remote Control: %s\n") % remote_name
                message += _(u"Steps executed: %d\n\n") % len(self.step_ids)
                message += _(u"Step Results:\n") + u"".join(
                    u"  %s\n" % r for r in step_results)
                message += _(u"\nResults:\n")
                if bag:
                    for k, v in bag.items():
                        s = unicode(v)
                        message += u"  • %s: %s%s\n" % (
                            k, s[:150], u"..." if len(s) > 150 else u"")
                else:
                    message += _(u"  (No data returned)\n")
                return {
                    'type': 'ir.actions.act_window.message',
                    'title': _(u'Test Successful'),
                    'message': message,
                    'is_html_message': False,
                    'close_button_title': False,
                    'buttons': [{
                        'type': 'ir.actions.act_window_close',
                        'name': _(u'Close'),
                    }],
                }
            else:
                message = _(u"Procedure Test Failed\n\n")
                message += _(u"Procedure: %s\n") % procedure_name
                message += _(u"Remote Control: %s\n\n") % remote_name
                if step_results:
                    message += _(u"Steps completed before failure:\n")
                    message += u"".join(u"  %s\n" % r for r in step_results)
                    message += u"\n"
                message += _(u"Error: %s") % unicode(e)
                return {
                    'type': 'ir.actions.act_window.message',
                    'title': _(u'Test Failed'),
                    'message': message,
                    'is_html_message': False,
                    'close_button_title': False,
                    'buttons': [{
                        'type': 'ir.actions.act_window_close',
                        'name': _(u'Close'),
                    }],
                }

    @api.multi
    def action_create_update_cron(self):
        for proc in self:
            vals = {
                'name': "RemoteControl: %s" % proc.name,
                'model': 'remotecontrol.procedure',
                'function': 'run',
                'args': '([%s])' % proc.id,
                'interval_number': proc.interval_number,
                'interval_type': proc.interval_type,
                'nextcall': proc.nextcall,
                'numbercall': proc.numbercall,
                'doall': False,
                'active': proc.active,
            }
            if proc.cron_id:
                proc.cron_id.write(vals)
            else:
                cron = self.env['ir.cron'].create(vals)
                proc.cron_id = cron.id
        return True

    def unlink(self):
        force_unlink = self.env.context.get('force_unlink', False)
        if (not force_unlink):
            for record in self:
                if record.readonly:
                    raise UserError(
                        _("You cannot delete a read-only Remote Control."))
        return super(RemoteControlProcedure, self).unlink()


class RemoteControlProcedureStep(models.Model):
    _name = 'remotecontrol.step'
    _description = 'Procedure Step'
    _order = 'procedure_id, sequence'

    name = fields.Char(
        string='Name',
        required=True,
    )

    procedure_id = fields.Many2one(
        string='Procedure',
        comodel_name='remotecontrol.procedure',
        required=True,
        ondelete='cascade',
    )

    action_id = fields.Many2one(
        string='Action',
        comodel_name='remotecontrol.action',
        required=True,
        ondelete='cascade',
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
