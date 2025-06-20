from odoo import api, SUPERUSER_ID


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    server_actions = env['ir.actions.server'].search([
        ('model_id.model', '=', 'worker_activity_self_monitoring.tray_icon')
    ])
    if server_actions:
        server_actions.unlink()

    views = env['ir.ui.view'].search([
        ('key', 'like', 'worker_activity_self_monitoring.%')
    ])
    if views:
        views.unlink()

    config_params = env['ir.config_parameter'].search([
        ('key', 'like', 'worker_activity_self_monitoring.%')
    ])
    if config_params:
        config_params.unlink()

    model_data = env['ir.model.data'].search([
        ('module', '=', 'worker_activity_self_monitoring')
    ])
    if model_data:
        model_data.unlink()

    crons = env['ir.cron'].search([
        ('name', 'like', 'worker_activity_self_monitoring.%')
    ])
    if crons:
        crons.unlink()

    print("Worker Activity Self Monitoring module uninstalled successfully.")
