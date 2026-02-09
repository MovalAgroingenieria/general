# Copyright 2017 LasLabs Inc.
# Copyright 2018 ACSONE
# Copyright 2018 Camptocamp
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import models


def setup_test_model(env, model_cls):
    """Initialize a dynamic test model in the registry.

    Courtesy of SBidoul from https://github.com/OCA/mis-builder :)
    """
    # Build the model class in the registry
    model_cls._build_model(env.registry, env.cr)  # pylint: disable=protected-access
    # Reconfigure all models to take the new one into account
    env.registry.setup_models(env.cr)
    # Initialize the specific model (fields, etc.)
    # pylint: disable=protected-access
    env.registry.init_models(
        env.cr, [model_cls._name], dict(env.context, update_custom_fields=True)
    )


def teardown_test_model(env, model_cls):
    """Deinitialize a dynamic test model from the registry.

    Courtesy of SBidoul from https://github.com/OCA/mis-builder :)
    """
    if not getattr(model_cls, "_teardown_no_delete", False):
        # Remove the model from the registry to avoid polluting other tests
        # pylint: disable=protected-access
        env.registry.models.pop(model_cls._name, None)
    env.registry.setup_models(env.cr)


class ResUsers(models.Model):
    """Dummy model for testing the comment.template mixin."""

    _name = "res.users"
    _description = "Test Res Users with Comment Template"
    _inherit = ["res.users", "comment.template"]
    _teardown_no_delete = True
