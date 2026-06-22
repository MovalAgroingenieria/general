RemoteControl: SAIH Ebro
========================

Remotecontrol for SAIH Ebro (Hydrological Information System of the Ebro Basin).

SAIH Ebro provides hydrological data via its OpenData REST API.

Features
--------

* OpenData REST API integration
* Lists available SAIH Ebro signals into a JSON attachment
* Fetches hydrological readings (water levels, flows, etc.) by signal code
* Configurable signal per sensor
* Automatic cron scheduling (e.g., every 15 minutes)
* Integration with MDM (Measurement Data Management)

Installation
------------

Install the module and configure a remotecontrol device with:

* **Remotecontrol level**: ``connection_params`` with ``api_key``
* **Sensor level**: ``remotecontrol_params`` with ``senal`` (e.g., "E282TIHQCAL4")

Usage
-----

1. Configure ``connection_params`` on the remote control record:

	 .. code-block:: json

		 {
			 "api_key": "your_api_key_here",
			 "default_start_date": "2026-06-19T00:00:00"
		 }

2. Run the ``SAIH Ebro: List Signals`` procedure to generate a JSON attachment
	 with all available signals.
3. Create a ``mdm.measurement.device`` assigned to the SAIH Ebro remotecontrol.
4. Add sensors with ``remotecontrol_params`` containing the signal code:

	 .. code-block:: json

		 {
			 "senal": "E282TIHQCAL4",
			 "start_date": "2026-06-19T00:00:00"
		 }

5. Set procedure schedule (e.g., every 15 minutes).
6. Enable procedure cron.
7. Readings will be auto-fetched and stored in ``mdm.measurement.device.sensor.reading``.

API endpoints
-------------

* ``GET /api/opendata/getListaSenalesArbol`` lists signals.
* ``GET /datos/apiopendata?senal=<senal>&inicio=<inicio>&apikey=<apikey>``
	fetches the 24 hours following ``inicio`` for one signal.

Contributors
------------

* Moval Agroingeniería
