#!/usr/bin/python3
from collections import defaultdict
from enum import Enum
from xml.etree import ElementTree

import requests as requests
import configparser
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


class OperatingVoltageStatus(Enum):
    NORMAL = 0
    UNKNOWN = 1
    OVERFLOW = 2


class State(Enum):
    CLOSED = 0
    OPEN = 1


def get_datapoint_enum_value(datapoint):
    if datapoint.attrib["type"] == "OPERATING_VOLTAGE_STATUS":
        return OperatingVoltageStatus(int(datapoint.attrib["value"]))
    if datapoint.attrib["type"] == "STATE":
        return State(int(datapoint.attrib["value"]))


def get_datapoint_value(datapoint):
    if datapoint.attrib["value"] == "":
        return None
    if datapoint.attrib["type"] == "RSSI_DEVICE":
        # The CCU returns an offset rssi value here. See https://forum.fhem.de/index.php?topic=106900.0
        return int(datapoint.attrib["value"]) - 256
    if datapoint.attrib["valuetype"] == "2":
        return True if datapoint.attrib["value"] == "true" else False
    if datapoint.attrib["valuetype"] == "4":
        return float(datapoint.attrib["value"])
    if datapoint.attrib["valuetype"] == "8":
        return int(datapoint.attrib["value"])
    if datapoint.attrib["valuetype"] == "16":
        return get_datapoint_enum_value(datapoint)


def get_data_from_device_state(device_state):
    device_meta = {}
    for datapoint in device_state[0]:
        device_meta[datapoint.attrib["type"]] = get_datapoint_value(datapoint)

    for datapoint in device_state[1]:
        device_meta[datapoint.attrib["type"]] = get_datapoint_value(datapoint)

    return device_meta


def get_room_from_device(device, id_room_list):
    for channel in device:
        channel_id = channel.attrib["ise_id"]
        if channel_id in id_room_list:
            return id_room_list[channel_id]


def get_state_dict():
    rooms = defaultdict(dict)

    id_room_list = {}
    roomlist_text = requests.get(f"{config['homematic']['ccu_url']}/config/xmlapi/roomlist.cgi").text
    roomlist = ElementTree.fromstring(roomlist_text)
    for room in roomlist:
        for channel in room:
            id_room_list[channel.attrib["ise_id"]] = room.attrib["name"]

    devicelist_text = requests.get(f"{config['homematic']['ccu_url']}/config/xmlapi/devicelist.cgi").text
    devices = ElementTree.fromstring(devicelist_text)

    for device in devices:
        device_name = device.attrib["name"]
        device_id = device.attrib["ise_id"]
        device_type = device.attrib["device_type"]
        device_room = get_room_from_device(device, id_room_list)

        if not device_room:
            continue

        state_text = requests.get(
            f"{config['homematic']['ccu_url']}/config/xmlapi/state.cgi", params={"device_id": device_id}
        ).text
        device_state = ElementTree.fromstring(state_text)[0]

        rooms[device_room][device_name] = {
            "device_type": device_type,
            "device_state": get_data_from_device_state(device_state),
        }

    return dict(rooms)


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read("config.ini")
    home_state = get_state_dict()

    data = []
    for room_name, devices in home_state.items():
        for device_name, device in devices.items():
            device_type = device["device_type"]
            device_state = device["device_state"]

            # Window Contact
            if device_type in ["HMIP-SWDO", "HmIP-SWDM"]:
                point = (
                    Point("window")
                    .tag("room", room_name)
                    .tag("device", device_name)
                    .field("state", device_state["STATE"].name == "OPEN")
                    .field("rssi", device_state["RSSI_DEVICE"])
                    .field("lowbat", device_state["LOW_BAT"])
                    .field("unreach", device_state["UNREACH"])
                )
                data.append(point)

            # Thermostat
            if device_type in ["HmIP-eTRV-B"]:
                point = (
                    Point("thermostat")
                    .tag("room", room_name)
                    .tag("device", device_name)
                    .field("temperature", device_state["ACTUAL_TEMPERATURE"])
                    .field("target_temperature", device_state["SET_POINT_TEMPERATURE"])
                    .field("valve_position", device_state["LEVEL"])
                    .field("rssi", device_state["RSSI_DEVICE"])
                    .field("lowbat", device_state["LOW_BAT"])
                    .field("unreach", device_state["UNREACH"])
                )
                data.append(point)

    influxdb_client = InfluxDBClient(
        url=config["influxdb"]["url"],
        token=config["influxdb"]["token"],
        org=config["influxdb"]["org"]
    )
    influxdb_write_client = influxdb_client.write_api(write_options=SYNCHRONOUS)

    influxdb_write_client.write(
        bucket=config["influxdb"]["bucket"], org=config["influxdb"]["org"], record=data
    )
