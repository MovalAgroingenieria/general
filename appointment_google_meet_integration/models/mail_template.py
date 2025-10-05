# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    def send_mail(self, res_id, force_send=False, raise_exception=False,
                  email_values=None, email_layout_xmlid=None):
        """Intercept email sending for Google Meet appointments"""

        # Check if this is the base appointment booking template
        zehntech_ref = (
            'appointment_booking_ce.'
            'appointment_booking_confirmation_mail_template'
        )
        zehntech_template = self.env.ref(
            zehntech_ref, raise_if_not_found=False
        )

        if zehntech_template and self.id == zehntech_template.id:
            event = self.env['calendar.event'].browse(res_id)

            # If event should use Google Meet, don't send the base template
            if (event.booking_type_id and
                    event.booking_type_id._should_use_google_meet()):

                # Block the email - return False to prevent sending
                # The correct email was already sent by our controller
                return False

        return super().send_mail(
            res_id, force_send=force_send,
            raise_exception=raise_exception,
            email_values=email_values,
            email_layout_xmlid=email_layout_xmlid
        )
