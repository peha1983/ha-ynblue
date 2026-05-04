"""Constants for the YnBlue integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

from homeassistant.const import CONF_EMAIL, CONF_LANGUAGE, CONF_PASSWORD, Platform

DOMAIN: Final = "ynblue"
NAME: Final = "YnBlue"
MANUFACTURER: Final = "YNEOM"
DEFAULT_LANGUAGE: Final = "en"

API_BASE_URL: Final = "https://api.yneom-iot.com"
MQTT_HOST: Final = "mqtt.yneom-iot.com"
MQTT_PORT: Final = 443
MQTT_PATH: Final = "/mqtt"
MQTT_USERNAME: Final = "JWT-client"
MQTT_KEEPALIVE: Final = 60
INITIAL_SNAPSHOT_DELAY: Final = 1.0
SNAPSHOT_RESPONSE_TIMEOUT: Final = 10
METADATA_REFRESH_INTERVAL: Final = timedelta(seconds=30)
SNAPSHOT_REFRESH_INTERVAL: Final = timedelta(seconds=90)
COMMAND_SETTLE_DELAY: Final = 2.0
FORCE_MEASUREMENT_TOGGLE_DELAY: Final = 1.0
FORCE_MEASUREMENT_SETTLE_DELAY: Final = 5.0
RESTART_RECOVERY_DELAY: Final = 45.0

AUTH_REFRESH_MARGIN: Final = timedelta(minutes=5)
AUTH_REFRESH_FALLBACK: Final = timedelta(minutes=30)
MQTT_CONNECT_TIMEOUT: Final = 30

PLATFORMS: Final = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.LIGHT,
    Platform.BUTTON,
]

ENTRY_EMAIL: Final = CONF_EMAIL
ENTRY_PASSWORD: Final = CONF_PASSWORD
ENTRY_LANGUAGE: Final = CONF_LANGUAGE

FILTER_MODE_OPTIONS: Final = {
    0: "Off",
    1: "Auto",
    2: "Force",
    3: "Winter",
    4: "Manual",
}
HEATER_MODE_OPTIONS: Final = {
    0: "Off",
    1: "Regulation",
    2: "Force",
    3: "Manual",
}
CHEMICAL_MODE_OPTIONS: Final = {
    0: "Off",
    1: "Fixed Dosage",
    2: "Regulation",
    3: "Force",
}
PH_MODE_OPTIONS: Final = {
    0: "Off",
    1: "Regulation",
}
ELECTROLYSER_PROTECTION_OPTIONS: Final = {
    0: "None",
    1: "Low Temperature",
    2: "Advanced",
}

ENTITY_OBJECT_ID_BY_KEY: Final = {
    "temperature": "ynblue_water_temperature",
    "ph_measured": "ynblue_ph_measured",
    "chemical_measured": "ynblue_chemical_measured",
    "chemical_estimated": "ynblue_chemical_estimated",
    "ph_tank_level": "ynblue_ph_tank_level",
    "chemical_tank_level": "ynblue_chemical_tank_level",
    "wifi_rssi": "ynblue_wifi_signal",
    "last_cloud_contact": "ynblue_last_cloud_contact",
    "online": "ynblue_online",
    "filter_running": "ynblue_filter_running",
    "heater_running": "ynblue_heater_running",
    "electrolyser_running": "ynblue_electrolyser_running",
    "ph_sensor_problem": "ynblue_ph_sensor_problem",
    "chemical_sensor_problem": "ynblue_chemical_sensor_problem",
    "meteo_available": "ynblue_weather_data_available",
    "force_measurement_active": "ynblue_force_measurement_active",
    "pool_volume": "ynblue_pool_volume",
    "ph_target": "ynblue_ph_target",
    "chemical_target": "ynblue_chemical_target",
    "heater_target": "ynblue_heater_target",
    "filter_mode": "ynblue_filter_mode",
    "heater_mode": "ynblue_heater_mode",
    "chemical_mode": "ynblue_chemical_mode",
    "ph_mode": "ynblue_ph_mode",
    "electrolyser_protection_mode": "ynblue_electrolyser_protection_mode",
    "robot": "ynblue_robot",
    "swim_jet": "ynblue_swim_jet",
    "fountain": "ynblue_fountain",
    "aux_switch": "ynblue_aux_switch",
    "aux_switch_2": "ynblue_aux_switch_2",
    "electrolyser_temp_protection": "ynblue_electrolyser_low_temperature_protection",
    "light": "ynblue_light",
    "light2": "ynblue_light_2",
    "rgb_light": "ynblue_rgb_light",
    "request_snapshot": "ynblue_request_snapshot",
    "force_measurement": "ynblue_force_measurement",
    "restart_controller": "ynblue_restart_controller",
    "cycle_rgb_program": "ynblue_cycle_rgb_program",
    "inject_ph": "ynblue_inject_ph_1l",
    "stop_ph_injection": "ynblue_stop_ph_injection",
    "reset_filter_consumption": "ynblue_reset_filter_consumption",
    "reset_ph_consumption": "ynblue_reset_ph_consumption",
    "reset_chemical_consumption": "ynblue_reset_chemical_consumption",
}

REDACT_CONFIG: Final = {"email", "password", "token", "jwt", "registrationString"}
