.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==========================
Base Remote Control Engine
==========================

Generic engine to integrate remote controls (REST / SQL) into Odoo 10.

This module provides a flexible framework for connecting Odoo with external systems through REST APIs or SQL databases.
It enables you to create reusable actions, chain them in procedures, and schedule automated executions.

Key Features
============

* **REST/SQL Connections**: Configure connections to external systems with retry and timeout policies
* **Action Repository**: Create Python code snippets with robust error handling and rate limiting
* **Procedure Orchestration**: Chain actions in a specific order, sharing data between steps
* **Scheduling**: Run procedures immediately or schedule them with cron jobs
* **Security**: Two-tier permission system with User and Manager roles
* **Audit Trail**: Full logging of all operations through mail.thread integration
* **Test Mode**: Safe testing of actions and procedures without affecting data (dry-run)

Technical Overview
==================

The module is structured around three main models:

1. **RemoteControl** - Connection profiles with configuration for external systems:

   * REST or SQL connection types
   * Connection parameters (credentials, timeouts, etc.)
   * Retry policies and rate limiting

2. **RemoteControlAction** - Python code snippets that perform specific tasks:

   * Execute code with access to Odoo environment
   * Make HTTP requests with retry logic
   * Transform and process data
   * Custom error handling

3. **RemoteControlProcedure** - Orchestration of multiple actions:

   * Sequence multiple actions in order
   * Pass data between steps using a shared "bag"
   * Schedule execution with Odoo's cron system
   * Test procedures with transaction rollback (dry-run)

Installation
============

This module depends on:

* base
* mail
* web_ir_actions_act_window_message

No additional Python packages are required for basic functionality, though for SQL connections
you might need appropriate database drivers.

Configuration
=============

After installing the module:

1. Assign user permissions through the "Remote Control" category:

   * **User**: Can view remote connections, actions, and procedures
   * **Manager**: Full permissions to create, edit, and delete all records

2. Create Remote Control connections through the interface
3. Configure security settings for external connections

Usage
=====

Remote Controls
---------------

1. Navigate to Remote Control > Remotes
2. Create a new Remote Control with either REST or SQL type
3. Configure connection parameters (base URL, timeout, SSL verification, etc.)
4. For REST, provide JSON-encoded credentials in Connection Parameters
5. For SQL, provide connection string in Connection Parameters

Actions
-------

1. Navigate to Remote Control > Actions
2. Create a new Action linked to a Remote Control
3. Write Python code to interact with the external system
4. Available variables in action code:

   * **env**: Odoo environment for database operations
   * **self**: Current action record
   * **bag**: Dictionary to store/share data between actions
   * **base_url**: Base URL from remote control configuration
   * **timeout**: Timeout setting from remote control
   * **json**: JSON library for data serialization
   * **base64**: For encoding/decoding base64 data
   * **pytz**: Python timezone library
   * **request_retry**: Function for HTTP requests with retry logic
   * **upsert**: Helper function to create or update records

5. Use the "Test Execute" button to test your action

Procedures
----------

1. Navigate to Remote Control > Procedures
2. Create a new Procedure linked to a Remote Control
3. Add Steps, each referencing an Action, in the desired execution order
4. Test the procedure using the "Test Run" button (runs in a transaction that will be rolled back)
5. Execute the procedure with "Run Now" button for immediate execution
6. Schedule the procedure using the "Save Cron" button and configure execution frequency

Development Examples
====================

HTTP Requests
-------------

.. code-block:: python

    # Simple GET request
    response = request_retry('GET', base_url + '/api/data')
    bag['response_data'] = response.json()

    # POST with JSON payload
    payload = {'name': 'example', 'value': 123}
    response = request_retry('POST', base_url + '/api/create',
                            json=payload,
                            headers={'Content-Type': 'application/json'})
    bag['created_id'] = response.json().get('id')

    # Authentication example
    conn_params = json.loads(self.remote_id.connection_params or '{}')
    headers = {
        'Authorization': 'Bearer ' + conn_params.get('token', ''),
        'Accept': 'application/json'
    }
    response = request_retry('GET', base_url + '/api/protected',
                            headers=headers)

Database Operations
-------------------

.. code-block:: python

    # Create a new record
    partner = env['res.partner'].create({
        'name': 'API Customer',
        'email': 'api@example.com',
        'is_company': True
    })
    bag['partner_id'] = partner.id

    # Find and update records
    partners = env['res.partner'].search([('email', '=', 'api@example.com')])
    if partners:
        partners.write({'phone': '+1234567890'})
        bag['updated_count'] = len(partners)

    # Using the upsert helper
    result = upsert(
        'res.partner',
        {'email': 'api@example.com'},  # Key fields to identify existing record
        {'name': 'API Customer', 'phone': '+1234567890'}  # Other fields to update
    )
    bag['partner_id'] = result.id

Error Handling
--------------

.. code-block:: python

    # Safe API call with error handling
    try:
        response = request_retry('GET', base_url + '/api/risky-endpoint')
        if response.status_code == 200:
            bag['success'] = True
            bag['data'] = response.json()
        else:
            bag['success'] = False
            bag['error'] = "HTTP " + str(response.status_code) + ": " + response.text
    except Exception as e:
        bag['success'] = False
        bag['error'] = str(e)

Best Practices
==============

* Always use request_retry instead of direct requests for better reliability
* Store important data in bag to share between actions in procedures
* Handle errors gracefully and store error information in bag
* Use meaningful variable names and add comments for complex logic
* Test actions individually before adding them to procedures
* Use rate_limit_seconds for APIs with strict rate limiting
* Keep procedures focused on a single business process
* Document your integrations in the action and procedure names/descriptions

Credits
=======

 * Moval Agroingeniería S.L.

Contributors
------------
* Guillermo Amante <gamante@moval.es>
* Samuel Fernández <sfernandez@moval.es>
* Pablo García <pgarcia@moval.es>
* Alberto Hernández <ahernandez@moval.es>
* Eduardo Iniesta <einiesta@moval.es>
* Jesús Martínez <jmartinez@moval.es>
* Miguel Mora <mmora@moval.es>
* Miguel Ángel Rodríguez <marodriguez@moval.es>
* Juanu Sandoval <jsandoval@moval.es>
* Salvador Sánchez <ssanchez@moval.es>
* Jorge Vera <jvera@moval.es>

Maintainer
----------

.. image:: https://raw.githubusercontent.com/MovalAgroingenieria/public-assets/master/logos/logo_moval_small.png
   :target: http://moval.es
   :alt: Moval Agroingeniería

This module is maintained by Moval Agroingeniería.
