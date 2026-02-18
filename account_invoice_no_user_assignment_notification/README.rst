.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

===============================================
Account Invoice No User Assignment Notification
===============================================

Este módulo evita que se envíe notificación automática cuando se asigna un responsable (user_id) a una factura.

**Problema**
------------

Cuando se hace tracking del campo ``user_id`` en facturas, el sistema envía automáticamente un mensaje de notificación 
a través del método ``_message_auto_subscribe_notify`` que es visible en el chatter para todos los seguidores del 
documento, incluyendo proveedores o clientes que puedan estar siguiendo la factura.

Esto puede causar:

* Exposición de información interna a partners externos
* Confusión para los proveedores que reciben notificaciones no relevantes
* Mensajes no deseados visible en el chatter

**Solución**
------------

Este módulo sobreescribe el método ``_message_auto_subscribe_notify`` específicamente para el modelo ``account.invoice``,
desactivando el envío automático de notificaciones cuando se asigna un usuario responsable.

El tracking del cambio sigue funcionando y se registra en el historial del documento, pero sin generar el mensaje 
automático visible en el chatter que notifica a todos los seguidores.

**Uso**
-------

Simplemente instale el módulo. Una vez instalado, las asignaciones de usuario en facturas ya no generarán 
notificaciones automáticas a los seguidores.

Credits
=======

Contributors
------------

* Moval Agroingeniería <info@moval.es>

Maintainer
----------

This module is maintained by Moval Agroingeniería.
