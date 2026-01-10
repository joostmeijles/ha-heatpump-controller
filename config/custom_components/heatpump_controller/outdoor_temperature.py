"""Outdoor temperature management for the heatpump controller.

This module handles reading outdoor temperature sensors and matching them
to configured threshold mappings.
"""

import logging
from typing import Any, Dict, List, Optional
from homeassistant.core import HomeAssistant

from .temperature_reader import read_sensor_temperature

_LOGGER = logging.getLogger(__name__)


class OutdoorTemperatureManager:
    """Manages outdoor temperature reading and threshold matching."""

    def __init__(
        self,
        hass: HomeAssistant,
        outdoor_sensor: Optional[str] = None,
        outdoor_sensor_fallback: Optional[str] = None,
        outdoor_thresholds: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Initialize the outdoor temperature manager.
        
        Args:
            hass: Home Assistant instance
            outdoor_sensor: Entity ID of primary outdoor temperature sensor
            outdoor_sensor_fallback: Entity ID of fallback outdoor temperature sensor
            outdoor_thresholds: List of threshold mappings with temperature ranges
        """
        self.hass = hass
        self.outdoor_sensor = outdoor_sensor
        self.outdoor_sensor_fallback = outdoor_sensor_fallback
        self.outdoor_thresholds = outdoor_thresholds or []
        self.outdoor_temp: Optional[float] = None
        self.active_outdoor_mapping: Optional[Dict[str, Any]] = None

    def get_outdoor_temperature(self) -> Optional[float]:
        """
        Read outdoor temperature from sensor with fallback support.
        
        Returns:
            Outdoor temperature as float, or None if unavailable
        """
        # Try primary sensor first
        temp = read_sensor_temperature(self.hass, self.outdoor_sensor, "Outdoor")
        if temp is not None:
            self.outdoor_temp = temp
            return temp

        # Try fallback sensor if primary failed
        if self.outdoor_sensor_fallback:
            _LOGGER.info(
                "Primary outdoor sensor unavailable, trying fallback sensor %s",
                self.outdoor_sensor_fallback,
            )
            temp = read_sensor_temperature(
                self.hass, self.outdoor_sensor_fallback, "Outdoor fallback"
            )
            if temp is not None:
                self.outdoor_temp = temp
                return temp

        # Both sensors unavailable
        self.outdoor_temp = None
        return None

    def match_outdoor_threshold(self) -> None:
        """
        Match outdoor temperature to threshold mapping and update active mapping.
        
        Evaluates configured outdoor thresholds in order and applies the first matching range.
        Updates self.active_outdoor_mapping with the matched configuration.
        """
        outdoor_temp = self.get_outdoor_temperature()

        if outdoor_temp is None:
            if self.active_outdoor_mapping:
                _LOGGER.debug(
                    "Clearing active outdoor mapping (outdoor temp unavailable)"
                )
                self.active_outdoor_mapping = None
            return

        # Evaluate mappings in order, first match wins
        for mapping in self.outdoor_thresholds:
            min_temp = mapping.get("min_temp")
            max_temp = mapping.get("max_temp")

            # Determine if this mapping matches
            matches = False
            if min_temp is not None and max_temp is not None:
                matches = min_temp <= outdoor_temp < max_temp
            elif min_temp is not None:
                matches = outdoor_temp >= min_temp
            elif max_temp is not None:
                matches = outdoor_temp < max_temp
            else:
                # Fallback mapping (no min/max specified)
                matches = True

            if matches:
                # Only update and log when the active mapping actually changes
                if mapping != self.active_outdoor_mapping:
                    self.active_outdoor_mapping = mapping
                    _LOGGER.info(
                        "Applying outdoor threshold override: outdoor_temp=%.2f°C, mapping=%s. "
                        "Effective thresholds: before_heat=%.6f, before_off=%.6f",
                        outdoor_temp,
                        mapping,
                        mapping.get("threshold_before_heat", "N/A"),
                        mapping.get("threshold_before_off", "N/A"),
                    )
                return

        # No mapping matched
        if self.active_outdoor_mapping:
            _LOGGER.debug("Clearing active outdoor mapping (no mapping matched)")
            self.active_outdoor_mapping = None

    def get_active_mapping(self) -> Optional[Dict[str, Any]]:
        """
        Get the currently active outdoor threshold mapping.
        
        Returns:
            Active mapping dictionary, or None if no mapping is active
        """
        return self.active_outdoor_mapping

    def clear_active_mapping(self) -> None:
        """Clear the currently active outdoor threshold mapping."""
        if self.active_outdoor_mapping:
            _LOGGER.debug("Clearing active outdoor mapping")
            self.active_outdoor_mapping = None
