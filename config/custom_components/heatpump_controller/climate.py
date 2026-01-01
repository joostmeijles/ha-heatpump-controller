from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    ClimateEntityFeature,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import logging

from .config import RoomConfig, CONF_ROOMS, CONF_THRESHOLD

_LOGGER = logging.getLogger(__name__)


class HeatPumpThermostat(ClimateEntity):
    _attr_name = "Heat Pump Controller"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]

    def __init__(self, hass: HomeAssistant, rooms: list[RoomConfig], threshold: float) -> None:
        self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
        self._attr_hvac_mode = HVACMode.OFF
        self.hass = hass
        self.rooms = rooms
        self.threshold = threshold

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Disable manual temperature setting."""
        _LOGGER.info("Manual temperature changes are disabled.")

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Disable manual HVAC mode changes."""
        _LOGGER.info("Manual HVAC mode changes are disabled.")

    async def async_update(self):
        temps = self._read_room_temperatures()
        if temps:
            avg_temp, avg_target, avg_needed_temp = self._calculate_weighted_averages(
                temps)
            self._attr_current_temperature = avg_temp
            self._attr_target_temperature = avg_target
            self._update_hvac_mode(avg_needed_temp)

            self._attr_extra_state_attributes = {
                "avg_needed_temp": avg_needed_temp,
                "threshold": self,
            }
        self.async_write_ha_state()

    def _read_room_temperatures(self) -> list[tuple[float, float, float]]:
        """Read temperatures from all room sensors."""
        temps: list[tuple[float, float, float]] = []
        for room in self.rooms:
            climate_state: State | None = self.hass.states.get(room['sensor'])
            if climate_state:
                try:
                    room_name: str = climate_state.attributes.get(  # type: ignore
                        "friendly_name", room['sensor'])
                    temp_target: float = float(
                        climate_state.attributes.get(  # type: ignore
                            "temperature_target", 0.0))
                    temp = float(climate_state.state)
                    _LOGGER.info(
                        f"{room_name}: {temp}°C, target: {temp_target}°C")
                    temps.append((temp, temp_target, room['weight']))
                except ValueError:
                    _LOGGER.warning(
                        f"Invalid temperature for {room['sensor']}")
            else:
                _LOGGER.warning(f"Sensor {room['sensor']} not found")
        return temps

    def _calculate_weighted_averages(self, temps: list[tuple[float, float, float]]) -> tuple[float, float, float]:
        """
        Calculate weighted averages for current and target temperatures.
        temps: list of tuples (current_temp, target_temp, weight)
        Returns weighted averages for current temp, target temp, and needed temp.
        """
        total_weight = sum(weight for _, _, weight in temps)
        if total_weight == 0:
            return 0, 0, 0

        weighted_temp = sum(temp * weight for temp, _,
                            weight in temps) / total_weight
        weighted_target = sum(target * weight for _, target,
                              weight in temps) / total_weight

        # Calculate weighted needed temperatures
        weighted_needed_temp_values: list[float] = []
        for temp, target, weight in temps:
            needed = target - temp if target > temp else 0
            weighted = needed * weight
            weighted_needed_temp_values.append(weighted)
            _LOGGER.debug(
                f"Room: temp={temp}, target={target}, weight={weight}, "
                f"needed={needed}, weighted={weighted}"
            )

        weighted_needed_temp = sum(weighted_needed_temp_values) / total_weight

        _LOGGER.debug(
            f"Weighted temp: {weighted_temp:.2f}°C, weigthed target: {weighted_target:.2f}°C, average gap to target: {weighted_needed_temp:.2f}°C")
        return weighted_temp, weighted_target, weighted_needed_temp

    def _update_hvac_mode(self, avg_needed_temp: float) -> None:
        """Decide HVAC mode based on weighted average and thresholds."""
        # Turn heat ON if any room is below its target - threshold

        if avg_needed_temp < self.threshold:
            _LOGGER.info(
                f"Average needed temperature below threshold ({avg_needed_temp:.2f}°C < {self.threshold}°C). Turning heat OFF.")
            self._attr_hvac_mode = HVACMode.OFF
            return

        _LOGGER.info(
            f"Average needed temperature above threshold ({avg_needed_temp:.2f}°C >= {self.threshold}°C). Turning heat ON.")
        self._attr_hvac_mode = HVACMode.HEAT


async def async_setup_platform(hass: HomeAssistant, config: dict[str, Any], async_add_entities: AddEntitiesCallback, discovery_info: dict[str, Any] | None = None) -> None:
    rooms: list[RoomConfig] = config[CONF_ROOMS]
    threshold: float = config[CONF_THRESHOLD]

    async_add_entities([HeatPumpThermostat(hass, rooms, threshold)])
