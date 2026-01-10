"""Temperature reading functions for the heatpump controller.

This module handles reading temperature values from Home Assistant sensors.
"""

import logging
from typing import Sequence, Tuple, Optional, Dict, Any
from homeassistant.core import HomeAssistant, State

_LOGGER = logging.getLogger(__name__)


def read_sensor_temperature(
    hass: HomeAssistant, sensor: Optional[str], sensor_type: str
) -> Optional[float]:
    """
    Read temperature from a sensor entity.
    
    Args:
        hass: Home Assistant instance
        sensor: Entity ID of the sensor to read, or None
        sensor_type: Human-readable sensor type for logging (e.g., "Outdoor", "Room")
        
    Returns:
        Temperature value as float, or None if unavailable/invalid
    """
    if not sensor:
        _LOGGER.debug("%s sensor not configured", sensor_type)
        return None

    state: Optional[State] = hass.states.get(sensor)
    if not state:
        _LOGGER.debug("%s sensor %s not found", sensor_type, sensor)
        return None

    try:
        temp = float(state.state)
        _LOGGER.debug("%s sensor %s read successfully: %.2f°C", sensor_type, sensor, temp)
        return temp
    except (ValueError, TypeError):
        _LOGGER.debug(
            "%s sensor %s has non-numeric state: %s", sensor_type, sensor, state.state
        )
        return None


def read_room_temperatures(
    hass: HomeAssistant, rooms: Sequence[Dict[str, Any]]
) -> list[Tuple[float, float, float]]:
    """
    Read temperatures from all room sensors.
    
    Args:
        hass: Home Assistant instance
        rooms: Sequence of room configurations with 'sensor' and 'weight' keys
        
    Returns:
        List of tuples (current_temp, target_temp, weight) for each room with valid data
    """
    temps: list[Tuple[float, float, float]] = []
    for room in rooms:
        climate_state: Optional[State] = hass.states.get(room["sensor"])
        if climate_state:
            try:
                room_name: str = climate_state.attributes.get(  # type: ignore
                    "friendly_name", room["sensor"]
                )
                temp_target: float = float(
                    climate_state.attributes.get("temperature_target", 0.0)  # type: ignore
                )
                temp = float(climate_state.state)
                _LOGGER.info(f"{room_name}: {temp}°C, target: {temp_target}°C")
                temps.append((temp, temp_target, room["weight"]))
            except ValueError:
                _LOGGER.warning(f"Invalid temperature for {room['sensor']}")
        else:
            _LOGGER.warning(f"Sensor {room['sensor']} not found")
    return temps
