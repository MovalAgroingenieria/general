.. image:: https://img.shields.io/badge/license-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

Mail Channel Mention Notifications
===================================

This module automatically posts messages to channels when users mention them using the ``#channel`` syntax in any ``mail.thread`` chatter (tasks, projects, invoices, etc.).


Features
--------

* **Automatic channel notifications**: When a user mentions a channel with ``#channel-name`` in any chatter, the message is automatically posted to that channel.
* **Clean message formatting**: The message sent to the channel includes:

  * Task name / Record reference
  * Original message body (without the channel mention)
  * "Ver tarea" button linking back to the original record

* **Multi-channel support**: Mention multiple channels in a single message; each will receive the notification.
* **No recursion**: Automatically prevents infinite loops by detecting when already inside a channel.


Usage
-----

Simply mention a channel in any chatter using the ``#`` syntax:

.. code-block:: text

    Revisar esto #Desarrollo Interno

The message will be posted to the "Desarrollo Interno" channel with:

* **Header**: "Tarea: [Task Name]"
* **Body**: "Revisar esto"
* **Button**: "Ver tarea" linking to the original record

Multiple channels can be mentioned:

.. code-block:: text

    #Soporte #Desarrollo Revisar esta incidencia urgente

The message will be posted to both "Soporte" and "Desarrollo" channels.


Bug tracking
============

Report issues through the maintainers of your deployment.
