from datetime import datetime, timedelta
from typing import Any, cast
import voluptuous as vol
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    ClimateEntityFeature,
)
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
import logging

from .const import CONTROLLER, DOMAIN, HEATPUMP_CONTROLLER_FRIENDLY_NAME, ControlAlgorithm
from .config import CONF_ON_OFF_SWITCH, CONF_THRESHOLD_BEFORE_HEAT, CONF_THRESHOLD_BEFORE_OFF, CONF_THRESHOLD_ROOM_NEEDS_HEAT, RoomConfig, CONF_ROOMS, CONF_OUTDOOR_SENSOR, CONF_OUTDOOR_SENSOR_FALLBACK, CONF_OUTDOOR_THRESHOLDS
from .calculations import calculate_weighted_averages, calculate_num_rooms_below_target, any_room_needs_heat
from .room_temperature_reader import read_room_temperatures
from .outdoor_temperature import OutdoorTemperatureManager
from .hvac_controller import HVACController

_LOGGER = logging.getLogger(__name__)


class HeatPumpThermostat(ClimateEntity):
    _attr_name = HEATPUMP_CONTROLLER_FRIENDLY_NAME
    _attr_unique_id = DOMAIN
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_should_poll = False  # Disable polling, use time-based updates

    def __init__(self, hass: HomeAssistant, rooms: list[RoomConfig], on_off_switch: str | None, threshold_before_heat: float, threshold_before_off: float, threshold_room_needs_heat: float, outdoor_sensor: str | None = None, outdoor_sensor_fallback: str | None = None, outdoor_thresholds: list[dict[str, Any]] | None = None) -> None:
        self._attr_hvac_mode = HVACMode.OFF
        self.hass = hass
        self.rooms = rooms
        self.on_off_switch = on_off_switch
        self._base_threshold_before_heat = threshold_before_heat
        self._base_threshold_before_off = threshold_before_off
        self._algorithm: ControlAlgorithm = ControlAlgorithm.MANUAL
        self._sensors: list[SensorEntity | BinarySensorEntity] = []
        
        # Initialize outdoor temperature manager
        self.outdoor_temp_manager = OutdoorTemperatureManager(
            hass, outdoor_sensor, outdoor_sensor_fallback, outdoor_thresholds
        )
        
        # Initialize HVAC controller
        self.hvac_controller = HVACController(
            threshold_before_heat, threshold_before_off, threshold_room_needs_heat
        )

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

    @property
    def outdoor_temp(self) -> float | None:
        """Return the current outdoor temperature."""
        return self.outdoor_temp_manager.outdoor_temp

    @property
    def active_outdoor_mapping(self) -> dict[str, Any] | None:
        """Return the active outdoor threshold mapping."""
        return self.outdoor_temp_manager.active_outdoor_mapping

    @property
    def threshold_room_needs_heat(self) -> float:
        """Return the per-room heat threshold."""
        return self.hvac_controller.threshold_room_needs_heat

    @property
    def is_paused(self) -> bool:
        """Return True if pause is active and not expired."""
        return self.hvac_controller.is_paused

    @property
    def threshold_before_heat(self) -> float:
        """Return effective threshold_before_heat (from active mapping or base)."""
        if self.outdoor_temp_manager.active_outdoor_mapping:
            return self.outdoor_temp_manager.active_outdoor_mapping.get(
                CONF_THRESHOLD_BEFORE_HEAT,
                self._base_threshold_before_heat,
            )
        return self._base_threshold_before_heat

    @property
    def threshold_before_off(self) -> float:
        """Return effective threshold_before_off (from active mapping or base)."""
        if self.outdoor_temp_manager.active_outdoor_mapping:
            return self.outdoor_temp_manager.active_outdoor_mapping.get(
                CONF_THRESHOLD_BEFORE_OFF,
                self._base_threshold_before_off,
            )
        return self._base_threshold_before_off

    def add_sensor(self, sensor: SensorEntity | BinarySensorEntity) -> None:
        _LOGGER.debug("Registering sensor %s with controller",
                      sensor.entity_id)
        self._sensors.append(sensor)

    def set_algorithm(self, algorithm: ControlAlgorithm) -> None:
        if self._algorithm != algorithm:
            _LOGGER.info("Switching control algorithm to %s", algorithm)
            self._algorithm = algorithm
            self.hass.async_create_task(self._async_control_loop())

    async def pause(self, duration_minutes: float) -> None:
        """Pause the controller for a given number of minutes."""
        self.hvac_controller.set_pause(duration_minutes)
        # Force immediate update
        await self._async_control_loop()

    async def _async_control_loop(self, now: datetime = dt_util.utcnow()) -> None:
        # Match outdoor temperature to threshold mapping only if outdoor temp algorithm is active
        if self.algorithm == ControlAlgorithm.WEIGHTED_AVERAGE_OUTDOOR_TEMP:
            self.outdoor_temp_manager.match_outdoor_threshold()
            # Update HVAC controller thresholds from active mapping
            self.hvac_controller.threshold_before_heat = self.threshold_before_heat
            self.hvac_controller.threshold_before_off = self.threshold_before_off
        else:
            # Clear active mapping if not using outdoor temp algorithm
            self.outdoor_temp_manager.clear_active_mapping()

        temps = read_room_temperatures(self.hass, cast(list[dict[str, Any]], self.rooms))
        if temps:
            avg_temp, avg_target, avg_needed_temp = calculate_weighted_averages(temps)
            self.any_room_needs_heat = any_room_needs_heat(
                temps, self.threshold_room_needs_heat
            )

            # Update entity state
            self._attr_current_temperature = avg_temp
            self._attr_target_temperature = avg_target
            
            # Update HVAC mode using the controller
            current_hvac = self._attr_hvac_mode if self._attr_hvac_mode is not None else HVACMode.OFF
            self._attr_hvac_mode = self.hvac_controller.update_hvac_mode(
                current_hvac, avg_needed_temp, self.any_room_needs_heat
            )

            self.current_temp_high_precision = round(avg_temp, 3)
            self.target_temp_high_precision = round(avg_target, 3)
            self.avg_needed_temp = round(avg_needed_temp, 3)
            self.num_rooms_below_target = calculate_num_rooms_below_target(temps)

            # Update extra state attributes
            pause_until = self.hvac_controller.get_pause_until()
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
                "pause_until": pause_until.isoformat() if pause_until else None,
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
    outdoor_sensor_fallback: str | None = config.get(CONF_OUTDOOR_SENSOR_FALLBACK)
    outdoor_thresholds: list[dict[str, Any]
                             ] | None = config.get(CONF_OUTDOOR_THRESHOLDS)

    return HeatPumpThermostat(
        hass,
        rooms,
        on_off_switch,
        threshold_before_heat,
        threshold_before_off,
        threshold_room_needs_heat,
        outdoor_sensor,
        outdoor_sensor_fallback,
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
