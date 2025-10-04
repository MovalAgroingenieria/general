# 2025 Moval Agroingeniería
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    def send_mail(self, res_id, force_send=False, raise_exception=False,
                  email_values=None, email_layout_xmlid=None):
        """Intercept email sending for Google Meet appointments"""

        zehntech_ref = (
            'appointment_booking_ce.'
            'appointment_booking_confirmation_mail_template'
        )
        zehntech_template = self.env.ref(
            zehntech_ref, raise_if_not_found=False
        )

        if zehntech_template and self.id == zehntech_template.id:
            event = self.env['calendar.event'].browse(res_id)

            if (event.booking_type_id and
                    event.booking_type_id._should_use_google_meet()):

                lang = self.env.context.get('lang', 'en_US')
                is_spanish = lang.startswith('es')

                module = 'appointment_google_meet_integration'
                if is_spanish:
                    template_name = (
                        'google_meet_appointment_booking_confirmation_mail_'
                        'template_es'
                    )
                else:
                    template_name = (
                        'google_meet_appointment_booking_confirmation_mail_'
                        'template'
                    )

                custom_ref = f'{module}.{template_name}'
                custom_template = self.env.ref(
                    custom_ref, raise_if_not_found=False
                )

                if custom_template:
                    return custom_template.send_mail(
                        res_id, force_send=force_send,
                        raise_exception=raise_exception,
                        email_values=email_values,
                        email_layout_xmlid=email_layout_xmlid
                    )

        return super().send_mail(
            res_id, force_send=force_send,
            raise_exception=raise_exception,
            email_values=email_values,
            email_layout_xmlid=email_layout_xmlid
        )
