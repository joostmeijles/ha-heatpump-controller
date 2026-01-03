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

ROOM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SENSOR): cv.entity_id,
        vol.Required(CONF_WEIGHT): vol.Coerce(float),
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
    }
)


class RoomConfig(TypedDict):
    sensor: str
    weight: float
