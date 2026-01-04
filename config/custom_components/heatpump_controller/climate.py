from datetime import datetime, timedelta
from typing import Any
import voluptuous as vol
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    ClimateEntityFeature,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, State, ServiceCall
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
import logging

from .const import DOMAIN
from .config import CONF_ON_OFF_SWITCH, CONF_THRESHOLD_BEFORE_HEAT, CONF_THRESHOLD_BEFORE_OFF, CONF_THRESHOLD_ROOM_NEEDS_HEAT, RoomConfig, CONF_ROOMS

_LOGGER = logging.getLogger(__name__)


class HeatPumpThermostat(ClimateEntity):
    _attr_name = "Heat Pump Controller"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_should_poll = False  # Disable polling, use time-based updates

    def __init__(self, hass: HomeAssistant, rooms: list[RoomConfig], on_off_switch: str | None, threshold_before_heat: float, threshold_before_off: float, threshold_room_needs_heat: float) -> None:
        self._attr_hvac_mode = HVACMode.OFF
        self.hass = hass
        self.rooms = rooms
        self.on_off_switch = on_off_switch
        self.threshold_before_heat = threshold_before_heat
        self.threshold_before_off = threshold_before_off
        self.threshold_room_needs_heat = threshold_room_needs_heat
        self._pause_until: datetime | None = None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Disable manual temperature setting."""
        _LOGGER.info("Manual temperature changes are disabled.")

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Disable manual HVAC mode changes."""
        _LOGGER.info("Manual HVAC mode changes are disabled.")

    async def async_added_to_hass(self) -> None:
        """Register periodic control loop."""
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._async_control_loop,
                timedelta(seconds=30),
            )
        )

    async def _async_control_loop(self, now: datetime) -> None:
        temps = self._read_room_temperatures()
        if temps:
            avg_temp, avg_target, avg_needed_temp = self._calculate_weighted_averages(
                temps)
            any_room_needs_heat = self._any_room_needs_heat(temps)

            # Update entity state
            self._attr_current_temperature = avg_temp
            self._attr_target_temperature = avg_target
            self._update_hvac_mode(avg_needed_temp, any_room_needs_heat)

            # Update extra state attributes
            self._attr_extra_state_attributes = {
                "current_temp_high_precision": round(avg_temp, 3),
                "target_temp_high_precision": round(avg_target, 3),
                "avg_needed_temp": round(avg_needed_temp, 3),
                "threshold_before_heat": self.threshold_before_heat,
                "threshold_before_off": self.threshold_before_off,
                "threshold_room_needs_heat": self.threshold_room_needs_heat,
                "num_rooms_below_target": self._calculate_num_rooms_below_target(temps),
                "any_room_needs_heat": any_room_needs_heat,
                "paused": self._is_paused(),
                "pause_until": self._pause_until.isoformat() if self._pause_until else None,
            }
        self.async_write_ha_state()
        await self._switch_heatpump()

    async def pause(self, duration_minutes: float) -> None:
        """Pause the controller for a given number of minutes."""
        self._pause_until = dt_util.utcnow() + timedelta(minutes=duration_minutes)
        _LOGGER.info(
            f"Heatpump controller paused until {self._pause_until.isoformat()}")

        # Force immediate update
        await self._async_control_loop(dt_util.utcnow())

    def _is_paused(self) -> bool:
        """Return True if pause is active and not expired."""
        return self._pause_until is not None and dt_util.utcnow() < self._pause_until

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

    def _calculate_num_rooms_below_target(self, temps: list[tuple[float, float, float]]) -> int:
        """Calculate number of rooms below their target temperatures."""
        count = 0
        for temp, target, _ in temps:
            if temp < target:
                count += 1
        return count

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
            f"Weighted temp: {weighted_temp:.3f}°C, weighted target: {weighted_target:.3f}°C, average gap to target: {weighted_needed_temp:.3f}°C")
        return weighted_temp, weighted_target, weighted_needed_temp

    def _any_room_needs_heat(
        self,
        temps: list[tuple[float, float, float]]
    ) -> bool:
        """Return True if any room is below target by threshold."""
        for current, target, _ in temps:
            diff = target - current
            if diff >= self.threshold_room_needs_heat:
                _LOGGER.debug(
                    "Room below target: current=%.3f target=%.3f diff=%.3f ≥ %.3f",
                    current,
                    target,
                    diff,
                    self.threshold_room_needs_heat,
                )
                return True
        return False

    def _update_hvac_mode(self, avg_needed_temp: float, any_room_needs_heat: bool) -> None:
        """Decide HVAC mode based on weighted average and thresholds."""
        # Check if paused
        if self._is_paused():
            if self._attr_hvac_mode != HVACMode.OFF:
                _LOGGER.info("Controller paused → turning heat OFF")
                self._attr_hvac_mode = HVACMode.OFF
            return

        # Any room too cold → HEAT ON
        if any_room_needs_heat:
            if self._attr_hvac_mode == HVACMode.OFF:
                _LOGGER.info(
                    "Turning heat ON: at least one room is below target."
                )
                self._attr_hvac_mode = HVACMode.HEAT
            return

        # Average-based hysteresis logic
        if self._attr_hvac_mode == HVACMode.OFF and avg_needed_temp >= self.threshold_before_heat:
            _LOGGER.info(
                f"Turning heat ON. Average needed temperature above threshold ({avg_needed_temp:.3f}°C >= {self.threshold_before_heat}°C).")
            self._attr_hvac_mode = HVACMode.HEAT
            return

        if self._attr_hvac_mode == HVACMode.HEAT and avg_needed_temp <= self.threshold_before_off:
            _LOGGER.info(
                f"Turning heat OFF.Average needed temperature below threshold ({avg_needed_temp:.3f}°C <= {self.threshold_before_off}°C).")
            self._attr_hvac_mode = HVACMode.OFF
            return

        _LOGGER.info(
            f"No change needed. Mode is {self._attr_hvac_mode}. Average needed temperature is {avg_needed_temp:.3f}°C and thresholds are before HEAT: {self.threshold_before_heat}°C and before OFF: {self.threshold_before_off}°C.")

    async def _switch_heatpump(self) -> None:
        """Switch the heatpump on or off."""
        if not self.on_off_switch:
            _LOGGER.info("Heatpump switch not configured.")
            return

        state = self.hass.states.get(self.on_off_switch)

        if state is None:
            _LOGGER.warning("Switch not found")
            return

        is_on = state.state == "on"

        if self._attr_hvac_mode == HVACMode.HEAT and not is_on:
            _LOGGER.info("Turning heatpump switch ON")
            await self.hass.services.async_call(
                "switch",
                "turn_on",
                {"entity_id": state.entity_id},
            )

        elif self._attr_hvac_mode == HVACMode.OFF and is_on:
            _LOGGER.info("Turning heatpump switch OFF")
            await self.hass.services.async_call(
                "switch",
                "turn_off",
                {"entity_id": state.entity_id},
            )


async def async_setup_platform(hass: HomeAssistant, config: dict[str, Any], async_add_entities: AddEntitiesCallback, discovery_info: dict[str, Any] | None = None) -> None:
    rooms: list[RoomConfig] = config[CONF_ROOMS]
    on_off_switch: str | None = config.get(CONF_ON_OFF_SWITCH)
    threshold_before_heat: float = config[CONF_THRESHOLD_BEFORE_HEAT]
    threshold_before_off: float = config[CONF_THRESHOLD_BEFORE_OFF]
    threshold_room_needs_heat: float = config[CONF_THRESHOLD_ROOM_NEEDS_HEAT]

    thermostat = HeatPumpThermostat(
        hass, rooms, on_off_switch, threshold_before_heat, threshold_before_off, threshold_room_needs_heat)
    async_add_entities([thermostat])

    async def async_pause_service(call: ServiceCall) -> None:
        duration = call.data.get("duration", 30)
        await thermostat.pause(duration)

    hass.services.async_register(
        DOMAIN,
        "pause_heatpump",
        async_pause_service,
        schema=vol.Schema({
            vol.Optional("duration", default=30): vol.Coerce(float)
        })
    )
