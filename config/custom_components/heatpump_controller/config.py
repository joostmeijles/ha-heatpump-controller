from typing import TypedDict
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.const import CONF_PLATFORM

CONF_ROOMS = "rooms"
CONF_SENSOR = "sensor"
CONF_WEIGHT = "weight"
CONF_THRESHOLD_BEFORE_HEAT = "threshold_before_heat"
CONF_THRESHOLD_BEFORE_OFF = "threshold_before_off"
CONF_THRESHOLD_ROOM_NEEDS_HEAT = "threshold_room_needs_heat"
CONF_ON_OFF_SWITCH = "on_off_switch"
CONF_OUTDOOR_SENSOR = "outdoor_sensor"
CONF_OUTDOOR_SENSOR_FALLBACK = "outdoor_sensor_fallback"
CONF_OUTDOOR_THRESHOLDS = "outdoor_thresholds"
CONF_LWT_DEVIATION_ENTITY = "lwt_deviation_entity"
CONF_LWT_ACTUAL_SENSOR = "lwt_actual_sensor"
CONF_LWT_SETPOINT_SENSOR = "lwt_setpoint_sensor"
CONF_MAX_ROOM_SETPOINT = "max_room_setpoint"
CONF_LWT_DEVIATION_MIN = "lwt_deviation_min"
CONF_LWT_DEVIATION_MAX = "lwt_deviation_max"
CONF_MIN_OFF_TIME_MINUTES = "min_off_time_minutes"
CONF_LWT_OVERCAPACITY_THRESHOLD = "lwt_overcapacity_threshold"
CONF_LWT_OVERCAPACITY_DURATION_MINUTES = "lwt_overcapacity_duration_minutes"

ROOM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SENSOR): cv.entity_id,
        vol.Required(CONF_WEIGHT): vol.Coerce(float),
    }
)

OUTDOOR_THRESHOLD_SCHEMA = vol.Schema(
    {
        vol.Optional("min_temp"): vol.Coerce(float),
        vol.Optional("max_temp"): vol.Coerce(float),
        vol.Required(CONF_THRESHOLD_BEFORE_HEAT): vol.Coerce(float),
        vol.Required(CONF_THRESHOLD_BEFORE_OFF): vol.Coerce(float),
    }
)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PLATFORM): cv.string,
        vol.Optional(CONF_ON_OFF_SWITCH): cv.entity_id,
        vol.Required(CONF_ROOMS): vol.All(cv.ensure_list, [ROOM_SCHEMA]),
        vol.Required(CONF_THRESHOLD_BEFORE_HEAT): vol.Coerce(float),
        vol.Required(CONF_THRESHOLD_BEFORE_OFF): vol.Coerce(float),
        vol.Required(CONF_THRESHOLD_ROOM_NEEDS_HEAT): vol.Coerce(float),
        vol.Optional(CONF_OUTDOOR_SENSOR): cv.entity_id,
        vol.Optional(CONF_OUTDOOR_SENSOR_FALLBACK): cv.entity_id,
        vol.Optional(CONF_OUTDOOR_THRESHOLDS): vol.All(cv.ensure_list, [OUTDOOR_THRESHOLD_SCHEMA]),
        vol.Optional(CONF_LWT_DEVIATION_ENTITY): cv.entity_id,
        vol.Optional(CONF_LWT_ACTUAL_SENSOR): cv.entity_id,
        vol.Optional(CONF_LWT_SETPOINT_SENSOR): cv.entity_id,
        vol.Optional(CONF_MAX_ROOM_SETPOINT, default=22.0): vol.Coerce(float),
        vol.Optional(CONF_LWT_DEVIATION_MIN, default=-10.0): vol.Coerce(float),
        vol.Optional(CONF_LWT_DEVIATION_MAX, default=10.0): vol.Coerce(float),
        vol.Optional(CONF_MIN_OFF_TIME_MINUTES, default=30): vol.Coerce(int),
        vol.Optional(CONF_LWT_OVERCAPACITY_THRESHOLD, default=1.0): vol.Coerce(float),
        vol.Optional(CONF_LWT_OVERCAPACITY_DURATION_MINUTES, default=60): vol.Coerce(int),
    }
)


class RoomConfig(TypedDict):
    sensor: str
    weight: float
