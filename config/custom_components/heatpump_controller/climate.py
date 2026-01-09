from datetime import datetime, timedelta
from typing import Any
import voluptuous as vol
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    ClimateEntityFeature,
)
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, State, ServiceCall
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
import logging

from .const import CONTROLLER, DOMAIN, HEATPUMP_CONTROLLER_FRIENDLY_NAME, ControlAlgorithm
from .config import (
    CONF_ON_OFF_SWITCH,
    CONF_THRESHOLD_BEFORE_HEAT,
    CONF_THRESHOLD_BEFORE_OFF,
    CONF_THRESHOLD_ROOM_NEEDS_HEAT,
    CONF_OUTDOOR_SENSOR,
    CONF_OUTDOOR_THRESHOLDS,
    CONF_MIN_TEMP,
    CONF_MAX_TEMP,
    RoomConfig,
    CONF_ROOMS,
)

_LOGGER = logging.getLogger(__name__)


class HeatPumpThermostat(ClimateEntity):
    _attr_name = HEATPUMP_CONTROLLER_FRIENDLY_NAME
    _attr_unique_id = DOMAIN
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_should_poll = False  # Disable polling, use time-based updates

    def __init__(self, hass: HomeAssistant, rooms: list[RoomConfig], on_off_switch: str | None, threshold_before_heat: float, threshold_before_off: float, threshold_room_needs_heat: float, outdoor_sensor: str | None = None, outdoor_thresholds: list[dict[str, Any]] | None = None) -> None:
        self._attr_hvac_mode = HVACMode.OFF
        self.hass = hass
        self.rooms = rooms
        self.on_off_switch = on_off_switch
        self._base_threshold_before_heat = threshold_before_heat
        self._base_threshold_before_off = threshold_before_off
        self.threshold_room_needs_heat = threshold_room_needs_heat
        self.outdoor_sensor = outdoor_sensor
        self.outdoor_thresholds = outdoor_thresholds or []
        self.outdoor_temp: float | None = None
        self.active_outdoor_mapping: dict[str, Any] | None = None
        self._pause_until: datetime | None = None
        self._algorithm: ControlAlgorithm = ControlAlgorithm.MANUAL
        self._sensors: list[SensorEntity | BinarySensorEntity] = []

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

    @property
    def algorithm(self) -> ControlAlgorithm:
        """Return the currently active control algorithm."""
        return self._algorithm

    def add_sensor(self, sensor: SensorEntity | BinarySensorEntity) -> None:
        _LOGGER.debug("Registering sensor %s with controller",
                      sensor.entity_id)
        self._sensors.append(sensor)

    def set_algorithm(self, algorithm: ControlAlgorithm) -> None:
        if self._algorithm != algorithm:
            _LOGGER.info("Switching control algorithm to %s", algorithm)
            self._algorithm = algorithm
            self.hass.async_create_task(self._async_control_loop())

    async def _async_control_loop(self, now: datetime = dt_util.utcnow()) -> None:
        temps = self._read_room_temperatures()
        if temps:
            avg_temp, avg_target, avg_needed_temp = self._calculate_weighted_averages(
                temps)
            self.any_room_needs_heat = self._any_room_needs_heat(temps)

            # Update entity state
            self._attr_current_temperature = avg_temp
            self._attr_target_temperature = avg_target
            self._update_hvac_mode(avg_needed_temp, self.any_room_needs_heat)

            self.current_temp_high_precision = round(avg_temp, 3)
            self.target_temp_high_precision = round(avg_target, 3)
            self.avg_needed_temp = round(avg_needed_temp, 3)
            self.num_rooms_below_target = self._calculate_num_rooms_below_target(
                temps)

            # Update extra state attributes
            self._attr_extra_state_attributes = {
                "algorithm": self.algorithm.value,
                "current_temp_high_precision": self.current_temp_high_precision,
                "target_temp_high_precision": self.target_temp_high_precision,
                "avg_needed_temp": self.avg_needed_temp,
                "threshold_before_heat": self.threshold_before_heat,
                "threshold_before_off": self.threshold_before_off,
                "threshold_room_needs_heat": self.threshold_room_needs_heat,
                "num_rooms_below_target": self.num_rooms_below_target,
                "any_room_needs_heat": self.any_room_needs_heat,
                "paused": self.is_paused,
                "pause_until": self._pause_until.isoformat() if self._pause_until else None,
            }
        self.async_write_ha_state()

        for sensor in self._sensors:
            _LOGGER.debug("Updating sensor %s", sensor.entity_id)
            sensor.async_write_ha_state()

        if self.algorithm == ControlAlgorithm.MANUAL:
            _LOGGER.info(
                "Manual algorithm selected, skipping automatic control.")
        else:
            await self._switch_heatpump()

    async def pause(self, duration_minutes: float) -> None:
        """Pause the controller for a given number of minutes."""
        self._pause_until = dt_util.utcnow() + timedelta(minutes=duration_minutes)
        _LOGGER.info(
            f"Heatpump controller paused until {self._pause_until.isoformat()}")

        # Force immediate update
        await self._async_control_loop()

    @property
    def is_paused(self) -> bool:
        """Return True if pause is active and not expired."""
        return self._pause_until is not None and dt_util.utcnow() < self._pause_until

    @property
    def threshold_before_heat(self) -> float:
        """Return effective threshold_before_heat (with outdoor override if applicable)."""
        self._match_outdoor_threshold()
        if self.active_outdoor_mapping and CONF_THRESHOLD_BEFORE_HEAT in self.active_outdoor_mapping:
            return self.active_outdoor_mapping[CONF_THRESHOLD_BEFORE_HEAT]
        return self._base_threshold_before_heat

    @property
    def threshold_before_off(self) -> float:
        """Return effective threshold_before_off (with outdoor override if applicable)."""
        self._match_outdoor_threshold()
        if self.active_outdoor_mapping and CONF_THRESHOLD_BEFORE_OFF in self.active_outdoor_mapping:
            return self.active_outdoor_mapping[CONF_THRESHOLD_BEFORE_OFF]
        return self._base_threshold_before_off

    def _get_outdoor_temperature(self) -> float | None:
        """Read outdoor temperature from configured sensor."""
        if not self.outdoor_sensor:
            _LOGGER.debug("Outdoor sensor not configured")
            return None

        state: State | None = self.hass.states.get(self.outdoor_sensor)
        if not state:
            _LOGGER.debug("Outdoor sensor %s not found", self.outdoor_sensor)
            return None

        try:
            return float(state.state)
        except (ValueError, TypeError):
            _LOGGER.debug("Outdoor sensor %s has non-numeric state: %s", self.outdoor_sensor, state.state)
            return None

    def _match_outdoor_threshold(self) -> None:
        """Match current outdoor temperature to a threshold override mapping."""
        outdoor_temp = self._get_outdoor_temperature()
        self.outdoor_temp = outdoor_temp

        if outdoor_temp is None:
            if self.active_outdoor_mapping is not None:
                _LOGGER.debug("Clearing active outdoor mapping (sensor unavailable/non-numeric)")
                self.active_outdoor_mapping = None
            return

        # Iterate configured outdoor_thresholds in order; first match wins
        for mapping in self.outdoor_thresholds:
            min_temp = mapping.get(CONF_MIN_TEMP)
            max_temp = mapping.get(CONF_MAX_TEMP)

            # Determine if this mapping matches
            matches = True
            if min_temp is not None and outdoor_temp < min_temp:
                matches = False
            if max_temp is not None and outdoor_temp >= max_temp:
                matches = False

            if matches:
                # Check if mapping actually changed
                if self.active_outdoor_mapping != mapping:
                    self.active_outdoor_mapping = mapping
                    # Log INFO when override is applied
                    effective_before_heat = mapping.get(CONF_THRESHOLD_BEFORE_HEAT, self._base_threshold_before_heat)
                    effective_before_off = mapping.get(CONF_THRESHOLD_BEFORE_OFF, self._base_threshold_before_off)
                    _LOGGER.info(
                        "Applying outdoor threshold override: outdoor_temp=%.2f°C, mapping=%s. Effective thresholds: before_heat=%.6f, before_off=%.6f",
                        outdoor_temp,
                        mapping,
                        effective_before_heat,
                        effective_before_off
                    )
                return

        # No match found, clear active mapping
        if self.active_outdoor_mapping is not None:
            _LOGGER.debug("Clearing active outdoor mapping (no matching threshold)")
            self.active_outdoor_mapping = None

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
        if self.is_paused:
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


def create_from_config(hass: HomeAssistant, config: dict[str, Any]) -> HeatPumpThermostat:
    rooms: list[RoomConfig] = config[CONF_ROOMS]
    on_off_switch: str | None = config.get(CONF_ON_OFF_SWITCH)
    threshold_before_heat: float = config[CONF_THRESHOLD_BEFORE_HEAT]
    threshold_before_off: float = config[CONF_THRESHOLD_BEFORE_OFF]
    threshold_room_needs_heat: float = config[CONF_THRESHOLD_ROOM_NEEDS_HEAT]
    outdoor_sensor: str | None = config.get(CONF_OUTDOOR_SENSOR)
    outdoor_thresholds: list[dict[str, Any]] | None = config.get(CONF_OUTDOOR_THRESHOLDS)

    return HeatPumpThermostat(
        hass,
        rooms,
        on_off_switch,
        threshold_before_heat,
        threshold_before_off,
        threshold_room_needs_heat,
        outdoor_sensor,
        outdoor_thresholds,
    )


async def async_setup_platform(hass: HomeAssistant, config: dict[str, Any], async_add_entities: AddEntitiesCallback, discovery_info: dict[str, Any] | None = None) -> None:
    controller: HeatPumpThermostat = hass.data[DOMAIN][CONTROLLER]
    async_add_entities([controller])

    async def async_pause_service(call: ServiceCall) -> None:
        duration = call.data.get("duration", 30)
        await controller.pause(duration)

    hass.services.async_register(
        DOMAIN,
        "pause_heatpump",
        async_pause_service,
        schema=vol.Schema({
            vol.Optional("duration", default=30): vol.Coerce(float)
        })
    )
