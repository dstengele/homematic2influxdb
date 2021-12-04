# Homematic to InfluxDB
This project can be used to get data from a Homematic System (IP and Non-IP) into InfluxDB. The two scripts are supposed
to be used as a cron job or as a Timer Unit.

## Dependencies
Both scripts depend on the [influxdb_client](https://github.com/influxdata/influxdb-client-python) library.

### main.py
To get the Data from the CCU, you need to install the [XML-API Addon](https://github.com/homematic-community/XML-API) on
your CCU. Make sure to restrict network access to the CCU, as this Addon does **not** have any authentication.

### main_ip.py
This additionally depends on [homematicip](https://github.com/coreGreenberet/homematicip-rest-api), which sadly has been
discontinued, but as I personally don't use HmIP anymore, I have not yet looked for a replacement. PRs are welcome!

To use main_ip.py, you will first have to get an authentication token. The required procedure is described
[here](https://homematicip-rest-api.readthedocs.io/en/latest/gettingstarted.html#getting-the-auth-token).