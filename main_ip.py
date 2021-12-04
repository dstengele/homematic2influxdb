#!/usr/bin/python3
import configparser

import homematicip
from homematicip.device import HeatingThermostat, ShutterContactMagnetic, ShutterContact
from homematicip.home import Home
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

config = homematicip.find_and_load_config_file()

config = configparser.ConfigParser()
config.read("config-hmip.ini")

home = Home()
home.set_auth_token(config.auth_token)
home.init(config.access_point)

home.get_current_state()
data = []

for group in home.groups:
    if group.groupType != "META":
        continue
    for device in group.devices:
        if isinstance(device, HeatingThermostat):
            point = (
                Point("thermostat")
                .tag("room", group.label)
                .tag("device", device.label)
                .field("temperature", device.valveActualTemperature)
                .field("target_temperature", device.setPointTemperature)
                .field("valve_position", device.valvePosition)
                .field("rssi", device.rssiDeviceValue)
                .field("lowbat", device.lowBat)
                .field("unreach", device.unreach)
            )
            data.append(point)
        if isinstance(device, ShutterContactMagnetic) or isinstance(
            device, ShutterContact
        ):
            point = (
                Point("window")
                .tag("room", group.label)
                .tag("device", device.label)
                .field("state", device.windowState == "OPEN")
                .field("rssi", device.rssiDeviceValue)
                .field("lowbat", device.lowBat)
                .field("unreach", device.unreach)
            )

            data.append(point)

influxdb_client = InfluxDBClient(
    url=config["influxdb"]["url"],
    token=config["influxdb"]["token"],
    org=config["influxdb"]["org"],
    debug=True,
)
influxdb_write_client = influxdb_client.write_api(write_options=SYNCHRONOUS)

influxdb_write_client.write(
    bucket=config["influxdb"]["bucket"], org=config["influxdb"]["org"], record=data
)
