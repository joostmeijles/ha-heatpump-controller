"""HVAC control logic for the heatpump controller.

This module handles HVAC mode decision logic including hysteresis,
pause state, and override conditions.
"""

import logging
from datetime import datetime
from typing import Optional
from homeassistant.components.climate.const import HVACMode
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)


class HVACController:
    """Manages HVAC mode decisions with hysteresis and pause logic."""

    def __init__(
        self,
        threshold_before_heat: float,
        threshold_before_off: float,
        threshold_room_needs_heat: float,
    ) -> None:
        """
        Initialize the HVAC controller.
        
        Args:
            threshold_before_heat: Temperature gap threshold to turn heat on
            threshold_before_off: Temperature gap threshold to turn heat off
            threshold_room_needs_heat: Per-room threshold for heat override
        """
        self._threshold_before_heat = threshold_before_heat
        self._threshold_before_off = threshold_before_off
        self.threshold_room_needs_heat = threshold_room_needs_heat
        self._pause_until: Optional[datetime] = None

    @property
    def threshold_before_heat(self) -> float:
        """Get the current heat-on threshold."""
        return self._threshold_before_heat

    @threshold_before_heat.setter
    def threshold_before_heat(self, value: float) -> None:
        """Set the heat-on threshold."""
        self._threshold_before_heat = value

    @property
    def threshold_before_off(self) -> float:
        """Get the current heat-off threshold."""
        return self._threshold_before_off

    @threshold_before_off.setter
    def threshold_before_off(self, value: float) -> None:
        """Set the heat-off threshold."""
        self._threshold_before_off = value

    @property
    def is_paused(self) -> bool:
        """Return True if pause is active and not expired."""
        return self._pause_until is not None and dt_util.utcnow() < self._pause_until

    def set_pause(self, duration_minutes: float) -> None:
        """
        Pause the controller for a given number of minutes.
        
        Args:
            duration_minutes: Number of minutes to pause
        """
        self._pause_until = dt_util.utcnow() + timedelta(minutes=duration_minutes)
        _LOGGER.info(f"Controller paused until {self._pause_until.isoformat()}")

    def get_pause_until(self) -> Optional[datetime]:
        """Get the pause expiration time."""
        return self._pause_until

    def update_hvac_mode(
        self,
        current_mode: HVACMode,
        avg_needed_temp: float,
        any_room_needs_heat: bool,
    ) -> HVACMode:
        """
        Decide HVAC mode based on weighted average and thresholds.
        
        Args:
            current_mode: Current HVAC mode
            avg_needed_temp: Weighted average temperature gap to target
            any_room_needs_heat: True if any room is significantly below target
            
        Returns:
            New HVAC mode (HEAT or OFF)
        """
        # Check if paused
        if self.is_paused:
            if current_mode != HVACMode.OFF:
                _LOGGER.info("Controller paused → turning heat OFF")
            return HVACMode.OFF

        # Any room too cold → HEAT ON
        if any_room_needs_heat:
            if current_mode == HVACMode.OFF:
                _LOGGER.info("Turning heat ON: at least one room is below target.")
            return HVACMode.HEAT

        # Average-based hysteresis logic
        if (
            current_mode == HVACMode.OFF
            and avg_needed_temp >= self._threshold_before_heat
        ):
            _LOGGER.info(
                f"Turning heat ON. Average needed temperature above threshold "
                f"({avg_needed_temp:.3f}°C >= {self._threshold_before_heat}°C)."
            )
            return HVACMode.HEAT

        if (
            current_mode == HVACMode.HEAT
            and avg_needed_temp < self._threshold_before_off
        ):
            _LOGGER.info(
                f"Turning heat OFF. Average needed temperature below threshold "
                f"({avg_needed_temp:.3f}°C <= {self._threshold_before_off}°C)."
            )
            return HVACMode.OFF

        _LOGGER.info(
            f"No change needed. Mode is {current_mode}. "
            f"Average needed temperature is {avg_needed_temp:.3f}°C and thresholds are "
            f"before HEAT: {self._threshold_before_heat}°C and "
            f"before OFF: {self._threshold_before_off}°C."
        )
        return current_mode


# Import timedelta for set_pause method
from datetime import timedelta
