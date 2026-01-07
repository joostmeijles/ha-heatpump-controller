from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from propcache import cached_property

from .climate import HeatPumpThermostat
from .const import DOMAIN, CONTROLLER


class HeatpumpBinarySensor(BinarySensorEntity):

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

    @property
    def is_on(self):  # type: ignore
        val = getattr(self.controller, self.attr, None)
        return val

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
        HeatpumpBinarySensor(
            controller, "any_room_needs_heat", "Any room below threshold"),
        HeatpumpBinarySensor(controller, "is_paused", "Paused")
    ])
