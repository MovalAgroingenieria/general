# pylint: disable=unused-argument


def post_init_hook(env):
    env.cr.execute(
        """
        UPDATE decimal_precision
           SET display_digits = COALESCE(display_digits, digits, 2)
    """
    )
