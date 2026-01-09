from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from propcache import cached_property
import json
import logging

from .climate import HeatPumpThermostat
from .const import DOMAIN, CONTROLLER

TEMPERATURE_SENSORS = {
    "current_temp_high_precision": "Average Temp",
    "target_temp_high_precision": "Avg Target Temp",
    "avg_needed_temp": "Avg Needed Temp",
    "threshold_before_heat": "Threshold Before Heat",
    "threshold_before_off": "Threshold Before Off",
    "threshold_room_needs_heat": "Threshold Room Needs Heat",
    "outdoor_temp": "Outdoor Temperature",
}

_LOGGER = logging.getLogger(__name__)


class TemperatureSensor(SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 3

    def __init__(self, controller: HeatPumpThermostat, attr: str, name: str) -> None:
        self.controller = controller
        self.attr = attr
        self._attr_name = name
        self._attr_unique_id = f"{controller.unique_id}_{attr}"

        # Register self with controller for updates
        controller.add_sensor(self)

    @property
    def available(self):  # type: ignore
        """Return True if the sensor has a valid value."""
        return getattr(self.controller, self.attr, None) is not None

    @cached_property
    def native_unit_of_measurement(self):
        return UnitOfTemperature.CELSIUS

    @property
    def native_value(self):  # type: ignore
        val = getattr(self.controller, self.attr, None)
        return val

    @cached_property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.controller.unique_id)},  # type: ignore
            name=f"{self.controller.name}"
        )


class RoomsBelowTargetSensor(SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0
    _attr_native_unit_of_measurement = "rooms"

    def __init__(self, hass: HomeAssistant, controller: HeatPumpThermostat, attr: str, name: str) -> None:
        self.controller = controller
        self.attr = attr
        self._attr_name = name
        self._attr_unique_id = f"{controller.unique_id}_{attr}"

        # Register self with controller for updates
        controller.add_sensor(self)

    @property
    def available(self):  # type: ignore
        """Return True if the sensor has a valid value."""
        return getattr(self.controller, self.attr, None) is not None

    @property
    def native_value(self):  # type: ignore
        val = getattr(self.controller, self.attr, None)
        return val

    @cached_property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.controller.unique_id)},  # type: ignore
            name=f"{self.controller.name}"
        )


class MappingSensor(SensorEntity):
    """Sensor that exposes the active outdoor mapping as JSON."""

    def __init__(self, controller: HeatPumpThermostat) -> None:
        self.controller = controller
        self._attr_name = "Active Outdoor Mapping"
        self._attr_unique_id = f"{controller.unique_id}_active_outdoor_mapping"

        # Register self with controller for updates
        controller.add_sensor(self)

    @property
    def available(self):  # type: ignore
        """Return True always - sensor is available even when value is None."""
        return True

    @property
    def native_value(self):  # type: ignore
        """Return compact JSON string of active mapping or None."""
        if self.controller.active_outdoor_mapping:
            # Return compact JSON with sorted keys
            return json.dumps(self.controller.active_outdoor_mapping, sort_keys=True, separators=(',', ':'))
        return None

    @cached_property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.controller.unique_id)},  # type: ignore
            name=f"{self.controller.name}"
        )


async def async_setup_platform(
        hass: HomeAssistant,
        config: dict[str, Any],
        async_add_entities: AddEntitiesCallback,
        discovery_info: dict[str, Any] | None = None):
    controller = hass.data[DOMAIN][CONTROLLER]

    async_add_entities([
        RoomsBelowTargetSensor(
            hass, controller, "num_rooms_below_target", "Rooms Below Target")
    ])

    async_add_entities([
        TemperatureSensor(controller, attr, name)
        for attr, name in TEMPERATURE_SENSORS.items()
    ])

    async_add_entities([
        MappingSensor(controller)
    ])
