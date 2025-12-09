# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
import json

_logger = logging.getLogger(__name__)


class BookingQueue(models.Model):
    _inherit = 'booking.queue'

    @api.model
    def create_from_web(self, event_data_dict):
        """
        Override to prevent duplicate bookings in queue.
        Check for existing bookings with same parameters before creating.
        """
        # Check for existing booking with same data
        existing = self.search([
            ('partner_email', '=', event_data_dict.get('partner_email')),
            ('booking_type_id', '=', event_data_dict.get('booking_type_id')),
            ('start_datetime', '=', event_data_dict.get('start_datetime')),
            ('state', 'in', ['pending', 'processing', 'done'])
        ], limit=1)

        if existing:
            _logger.info(
                f"Duplicate booking detected for {event_data_dict.get('partner_email')} "
                f"at {event_data_dict.get('start_datetime')}. Using existing queue record: {existing.name}")
            return existing

        return super(BookingQueue, self).create_from_web(event_data_dict)

    @api.model
    def create(self, vals):
        """
        Override create to add additional duplicate checks at database level
        """
        if 'partner_email' in vals and 'start_datetime' in vals and 'booking_type_id' in vals:
            # Check for duplicate in database
            existing = self.search([
                ('partner_email', '=', vals['partner_email']),
                ('booking_type_id', '=', vals['booking_type_id']),
                ('start_datetime', '=', vals['start_datetime']),
                ('state', 'in', ['pending', 'processing', 'done'])
            ], limit=1)

            if existing:
                _logger.warning(
                    f"Attempted to create duplicate booking queue entry. "
                    f"Email: {vals['partner_email']}, Start: {vals['start_datetime']}. "
                    f"Returning existing record: {existing.name}")
                return existing

        return super(BookingQueue, self).create(vals)