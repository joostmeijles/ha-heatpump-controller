from typing import Any
from functools import cached_property
from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONTROLLER, DOMAIN, ControlAlgorithm
from .climate import HeatpumpThermostat


class HeatpumpAlgorithmSelect(SelectEntity, RestoreEntity):
    _attr_name = "Algorithm"

    def __init__(self, controller: HeatpumpThermostat) -> None:
        self._controller = controller
        self._attr_current_option = controller.algorithm.label
        self._attr_unique_id = f"{controller.unique_id}_{self.name}"

    @cached_property
    def options(self):
        return [algo.label for algo in ControlAlgorithm]

    @property
    def current_option(self):  # type: ignore
        return self._controller.algorithm.label

    async def async_added_to_hass(self) -> None:
        """Restore the previously selected algorithm on startup."""
        await super().async_added_to_hass()

        state = await self.async_get_last_state()
        if state is not None and state.state in self.options:
            # Find and set the algorithm that matches the restored label
            for algo in ControlAlgorithm:
                if algo.label == state.state:
                    self._controller.set_algorithm(algo)
                    self._attr_current_option = state.state
                    break

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
    async_add_entities([HeatpumpAlgorithmSelect(controller)])
