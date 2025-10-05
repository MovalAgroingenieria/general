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
### Automatización:
- **Cron Job**: Se ejecuta diariamente para verificar clientes que superan el límite de días sin compra
- **Notificaciones automáticas**: Se envían una sola vez hasta resetear el estado
- **Reset automático**: Cuando un cliente hace una nueva compra confirmada, se resetea automáticamente el estado de notificación

### Acciones manuales:
- **Send Notification**: Botón para enviar notificación manual (con confirmación)
- **Reset Status**: Botón para resetear el estado de notificación (con confirmación, permite volver a notificar)
- **Auto-refresh**: Los campos se actualizan automáticamente sin necesidad de recargar la página

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

## Notas técnicas

- Las fechas se calculan basándose en órdenes de venta confirmadas (`state` en 'sale' o 'done')
- El cron job se ejecuta una vez por día
- Las notificaciones se envían solo una vez hasta resetear el estado manualmente
- **Reset automático**: El estado se resetea automáticamente cuando se confirma una nueva orden de venta
- **Actualización automática**: Los campos se refrescan automáticamente después de cada acción
- **JavaScript personalizado**: Incluye handler para recargar la vista sin pérdida de contexto
- **Confirmaciones**: Botones incluyen diálogos de confirmación para evitar acciones accidentales
- **Plantilla de email QWeb**: Usa sintaxis QWeb para compatibilidad multiidioma
- Compatible con Odoo 14.0

## Archivos JavaScript

El módulo incluye JavaScript personalizado (`notification_handler.js`) que:
- Detecta cuando se ejecutan las acciones de notificación
- Recarga automáticamente la vista después de la acción
- Mantiene el contexto del formulario
- No requiere refrescar manualmente la página