from typing import Any
from functools import cached_property
from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONTROLLER, DOMAIN, ControlAlgorithm
from .climate import HeatPumpThermostat


class HeatPumpAlgorithmSelect(SelectEntity):
    _attr_name = "Algorithm"

    def __init__(self, controller: HeatPumpThermostat) -> None:
        self._controller = controller
        self._attr_current_option = controller.algorithm.value
        self._attr_unique_id = f"{controller.unique_id}_{self.name}"

    @cached_property
    def options(self):
        return [algo.label for algo in ControlAlgorithm]

    @property
    def current_option(self):  # type: ignore
        return self._controller.algorithm.label

    async def async_select_option(self, option: str) -> None:
        algo = next(a for a in ControlAlgorithm if a.label == option)
        self._controller.set_algorithm(algo)
        self._attr_current_option = option
        self.async_write_ha_state()


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict[str, Any],
    async_add_entities: AddEntitiesCallback,
    discovery_info: dict[str, Any] | None = None,
) -> None:
    controller = hass.data[DOMAIN][CONTROLLER]
    async_add_entities([HeatPumpAlgorithmSelect(controller)])
