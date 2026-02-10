# Customer Purchase Follow-up

## Description

This module allows tracking customers who haven't made recent purchases and sending automatic or manual notifications to maintain commercial relationships.

## Features

### Customer configuration fields:
- **Enable Purchase Notifications**: Enables/disables notifications for this customer
- **Days Without Purchase Limit**: Maximum days without purchase before sending notification (configurable per customer)
- **Notification Users**: Users who will receive the notifications
- **Send Email Notification**: Send notification via email
- **Create CRM Opportunity**: Create CRM opportunity when notification is triggered

### Informational fields:
- **Last Purchase Date**: Date of the last confirmed purchase
- **Days Since Last Purchase**: Days elapsed since the last purchase
- **Client Notified**: Indicates if the customer has already been notified
- **Last Notification Date**: Date of the last notification sent

### Automation:
- **Cron Job**: Runs daily to check customers that exceed the days-without-purchase limit
- **Automatic notifications**: Sent once until the status is reset
- **Automatic reset**: When a customer makes a new confirmed purchase, the notification status is reset automatically

### Manual actions:
- **Send Notification**: Button to send manual notification (with confirmation)
- **Reset Status**: Button to reset notification status (with confirmation, allows notifying again)
- **Auto-refresh**: Fields update automatically without reloading the page

### Menus:
- **Sales > Purchase Follow-up > Customers with Follow-up**: List of customers with follow-up enabled
- **Sales > Purchase Follow-up > Customers Needing Follow-up**: Customers requiring notification

## Configuration

1. Activate **Enable Purchase Notifications** for desired customers
2. Configure **Days Without Purchase Limit** (default 30 days)
3. Select **Notification Users** who will receive notifications
4. Choose notification type:
    - **Send Email Notification**: For email delivery
    - **Create CRM Opportunity**: To create CRM opportunities

## Security

- Users in the **Sales / User** group have read and write access to follow-up fields
- Only applies to company-type records (`is_company = True`)

## Email Template

The module includes an email template with detailed customer information:
- Customer name
- Last purchase date
- Days without purchasing
- Configured limit
- Customer contact data

## Installation

1. Install the module from Apps
2. The system is disabled by default
3. Manually activate for each customer as needed

## Technical Notes

- Dates are calculated from confirmed sale orders (`state` in 'sale' or 'done')
- The cron job runs once per day
- Notifications are sent only once until the status is reset manually
- **Automatic reset**: Status is reset automatically when a new sale order is confirmed
- **Automatic refresh**: Fields are refreshed automatically after each action
- **Custom JavaScript**: Includes a handler to reload the view without losing context
- **Confirmations**: Buttons include confirmation dialogs to avoid accidental actions
- **QWeb email template**: Uses QWeb syntax for multi-language compatibility
- Compatible with Odoo 14.0

## JavaScript Files

The module includes custom JavaScript (`notification_handler.js`) that:
- Detects when notification actions are executed
- Reloads the view automatically after the action
- Preserves the form context
- Does not require manually refreshing the page