"""LWT Control logic for the heatpump controller.

This module manages Leaving Water Temperature (LWT) control mode,
which controls room temperature by adjusting the LWT deviation on
the weather-dependent curve rather than simple on/off control.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
import numpy as np
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)


class LWTController:
    """Manages LWT Control mode logic."""

    def __init__(
        self,
        hass: HomeAssistant,
        lwt_deviation_entity: str,
        lwt_actual_sensor: str,
        lwt_setpoint_sensor: str,
        max_room_setpoint: float,
        lwt_deviation_min: float,
        lwt_deviation_max: float,
        min_off_time_minutes: int,
        lwt_overcapacity_threshold: float,
        lwt_overcapacity_duration_minutes: int,
    ) -> None:
        """
        Initialize the LWT controller.

        Args:
            hass: Home Assistant instance
            lwt_deviation_entity: Entity ID of the LWT deviation number entity
            lwt_actual_sensor: Entity ID of the actual LWT sensor
            lwt_setpoint_sensor: Entity ID of the LWT setpoint sensor
            max_room_setpoint: Maximum room temperature setpoint for TRV valves
            lwt_deviation_min: Minimum allowed LWT deviation
            lwt_deviation_max: Maximum allowed LWT deviation
            min_off_time_minutes: Minimum off time to prevent short-cycling
            lwt_overcapacity_threshold: LWT actual - setpoint threshold for overcapacity
            lwt_overcapacity_duration_minutes: Duration to sustain overcapacity before action
        """
        self.hass = hass
        self._lwt_deviation_entity = lwt_deviation_entity
        self._lwt_actual_sensor = lwt_actual_sensor
        self._lwt_setpoint_sensor = lwt_setpoint_sensor
        self._max_room_setpoint = max_room_setpoint
        self._lwt_deviation_min = lwt_deviation_min
        self._lwt_deviation_max = lwt_deviation_max
        self._min_off_time_minutes = min_off_time_minutes
        self._lwt_overcapacity_threshold = lwt_overcapacity_threshold
        self._lwt_overcapacity_duration_minutes = lwt_overcapacity_duration_minutes

        # State variables
        self._original_setpoints: dict[str, float] = {}  # entity_id -> original setpoint
        self._overcapacity_start: Optional[datetime] = None  # When overcapacity condition started
        self._off_since: Optional[datetime] = None  # When heatpump was turned off
        self._temp_history: list[tuple[datetime, float]] = []  # For trend calculation
        self._current_deviation: float = 0.0  # Current deviation value
        self._is_active: bool = False  # Whether LWT mode is currently active

    @property
    def is_active(self) -> bool:
        """Return True if LWT Control is currently active."""
        return self._is_active

    @property
    def current_deviation(self) -> float:
        """Return the current LWT deviation."""
        return self._current_deviation

    @property
    def is_overcapacity(self) -> bool:
        """Return True if overcapacity condition is currently met."""
        return self._check_overcapacity()

    @property
    def off_remaining_minutes(self) -> Optional[float]:
        """Return minutes remaining in minimum off period, or None if not off."""
        if self._off_since is None:
            return None

        off_duration = dt_util.utcnow() - self._off_since
        remaining = timedelta(minutes=self._min_off_time_minutes) - off_duration
        if remaining.total_seconds() > 0:
            return remaining.total_seconds() / 60.0
        return 0.0

    async def activate(self, rooms: list[dict[str, Any]]) -> None:
        """
        Called when entering LWT Control mode.
        Save and override room setpoints to max.

        Args:
            rooms: List of room configurations with sensor entity IDs
        """
        _LOGGER.info("Activating LWT Control mode")
        self._is_active = True
        self._original_setpoints.clear()

        for room in rooms:
            entity_id = room["sensor"]
            state = self.hass.states.get(entity_id)
            if state and state.attributes.get("temperature") is not None:
                original_temp = state.attributes.get("temperature")
                self._original_setpoints[entity_id] = original_temp
                _LOGGER.info(
                    f"Saving original setpoint for {entity_id}: {original_temp}°C"
                )

                # Set to max setpoint to force TRV valves fully open
                await self.hass.services.async_call(
                    "climate",
                    "set_temperature",
                    {"entity_id": entity_id, "temperature": self._max_room_setpoint},
                )
                _LOGGER.info(
                    f"Set {entity_id} to max setpoint: {self._max_room_setpoint}°C"
                )

    async def deactivate(self, rooms: list[dict[str, Any]]) -> None:
        """
        Called when leaving LWT Control mode.
        Restore original setpoints.

        Args:
            rooms: List of room configurations with sensor entity IDs
        """
        _LOGGER.info("Deactivating LWT Control mode")
        self._is_active = False

        for room in rooms:
            entity_id = room["sensor"]
            if entity_id in self._original_setpoints:
                original_temp = self._original_setpoints[entity_id]
                await self.hass.services.async_call(
                    "climate",
                    "set_temperature",
                    {"entity_id": entity_id, "temperature": original_temp},
                )
                _LOGGER.info(
                    f"Restored {entity_id} to original setpoint: {original_temp}°C"
                )

        self._original_setpoints.clear()
        self._overcapacity_start = None
        self._off_since = None
        self._temp_history.clear()

    def _get_lwt_actual(self) -> Optional[float]:
        """Get the current actual LWT from sensor."""
        state = self.hass.states.get(self._lwt_actual_sensor)
        if state is None or state.state in ("unknown", "unavailable"):
            return None
        try:
            return float(state.state)
        except (ValueError, TypeError):
            return None

    def _get_lwt_setpoint(self) -> Optional[float]:
        """Get the current LWT setpoint from sensor."""
        state = self.hass.states.get(self._lwt_setpoint_sensor)
        if state is None or state.state in ("unknown", "unavailable"):
            return None
        try:
            return float(state.state)
        except (ValueError, TypeError):
            return None

    def _check_overcapacity(self) -> bool:
        """
        Check if heatpump has been at minimum capacity for the required duration.

        Returns:
            True if overcapacity condition is met, False otherwise
        """
        lwt_actual = self._get_lwt_actual()
        lwt_setpoint = self._get_lwt_setpoint()

        if lwt_actual is None or lwt_setpoint is None:
            self._overcapacity_start = None
            return False

        currently_over = (lwt_actual - lwt_setpoint) >= self._lwt_overcapacity_threshold

        if currently_over:
            if self._overcapacity_start is None:
                self._overcapacity_start = dt_util.utcnow()
                _LOGGER.debug(
                    f"Overcapacity condition started: LWT actual ({lwt_actual}°C) - "
                    f"setpoint ({lwt_setpoint}°C) = {lwt_actual - lwt_setpoint:.2f}°C "
                    f">= threshold ({self._lwt_overcapacity_threshold}°C)"
                )

            duration = dt_util.utcnow() - self._overcapacity_start
            is_overcapacity = duration >= timedelta(
                minutes=self._lwt_overcapacity_duration_minutes
            )

            if is_overcapacity:
                _LOGGER.debug(
                    f"Overcapacity sustained for {duration.total_seconds() / 60:.1f} minutes"
                )

            return is_overcapacity
        else:
            if self._overcapacity_start is not None:
                _LOGGER.debug("Overcapacity condition ended")
            self._overcapacity_start = None
            return False

    def record_temperature(self, avg_temp: float) -> None:
        """
        Record average temperature for trend calculation.

        Args:
            avg_temp: Current average room temperature
        """
        now = dt_util.utcnow()
        self._temp_history.append((now, avg_temp))

        # Keep last 30 minutes of readings (assuming 30 second intervals = ~60 readings)
        cutoff = now - timedelta(minutes=30)
        self._temp_history = [
            (ts, temp) for ts, temp in self._temp_history if ts > cutoff
        ]

    def can_restart(self) -> bool:
        """
        Check if heatpump can restart.
        Must satisfy minimum off time and temperature trending down.

        Returns:
            True if heatpump can restart, False otherwise
        """
        if self._off_since is None:
            return True

        # Check minimum off time
        off_duration = dt_util.utcnow() - self._off_since
        if off_duration < timedelta(minutes=self._min_off_time_minutes):
            remaining = (
                timedelta(minutes=self._min_off_time_minutes) - off_duration
            ).total_seconds() / 60.0
            _LOGGER.debug(
                f"Minimum off time not met: {remaining:.1f} minutes remaining"
            )
            return False

        # Check temperature trend
        trending_down = self._is_temp_trending_down()
        if not trending_down:
            _LOGGER.debug("Temperature not trending down, cannot restart yet")
            return False

        _LOGGER.info("Conditions met for restart: min off time passed and temp trending down")
        return True

    def _is_temp_trending_down(self) -> bool:
        """
        Calculate if average temperature is trending downward using linear regression.

        Returns:
            True if temperature trend is negative (cooling), False otherwise
        """
        if len(self._temp_history) < 5:
            _LOGGER.debug(
                f"Not enough temperature history for trend calculation: {len(self._temp_history)} samples"
            )
            return True  # Assume trending down if not enough data

        # Convert to numpy arrays for linear regression
        times = np.array(
            [(ts - self._temp_history[0][0]).total_seconds() for ts, _ in self._temp_history]
        )
        temps = np.array([temp for _, temp in self._temp_history])

        # Calculate linear regression slope
        # y = mx + b, where m is the slope
        slope, _ = np.polyfit(times, temps, 1)

        _LOGGER.debug(
            f"Temperature trend slope: {slope:.6f}°C/second "
            f"({slope * 3600:.4f}°C/hour) over {len(self._temp_history)} samples"
        )

        # Negative slope means temperature is decreasing
        return slope < 0

    async def set_lwt_deviation(self, deviation: float) -> None:
        """
        Set the LWT deviation within configured bounds.

        Args:
            deviation: Desired LWT deviation value
        """
        clamped = max(self._lwt_deviation_min, min(self._lwt_deviation_max, deviation))

        if abs(clamped - self._current_deviation) > 0.01:  # Only log if changed significantly
            _LOGGER.info(
                f"Setting LWT deviation to {clamped:.2f}°C (requested: {deviation:.2f}°C, "
                f"range: [{self._lwt_deviation_min}, {self._lwt_deviation_max}])"
            )

        self._current_deviation = clamped

        await self.hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": self._lwt_deviation_entity, "value": clamped},
        )

    def calculate_deviation(self, avg_needed_temp: float) -> float:
        """
        Calculate appropriate LWT deviation based on heat demand.

        Maps avg_needed_temp (heat demand) to the deviation range.
        Higher avg_needed_temp (more heat needed) -> higher deviation
        Lower/negative avg_needed_temp (less heat needed) -> lower deviation

        Args:
            avg_needed_temp: Weighted average temperature gap (target - actual)

        Returns:
            Calculated LWT deviation
        """
        # Map avg_needed_temp to deviation range
        # Assume avg_needed_temp typically ranges from -1.0 to +1.0
        # Map this to deviation range linearly

        # Define typical expected range for avg_needed_temp
        temp_range = 1.0

        # Normalize avg_needed_temp to [-1, 1] range
        normalized = max(-1.0, min(1.0, avg_needed_temp / temp_range))

        # Map to deviation range
        deviation_range = self._lwt_deviation_max - self._lwt_deviation_min
        deviation_mid = (self._lwt_deviation_max + self._lwt_deviation_min) / 2.0

        deviation = deviation_mid + (normalized * deviation_range / 2.0)

        _LOGGER.debug(
            f"Calculated deviation: {deviation:.2f}°C from avg_needed_temp: {avg_needed_temp:.3f}°C "
            f"(normalized: {normalized:.3f})"
        )

        return deviation

    def mark_off(self) -> None:
        """Mark that the heatpump has been turned off."""
        if self._off_since is None:
            self._off_since = dt_util.utcnow()
            _LOGGER.info("Heatpump marked as OFF for minimum off time tracking")

    def clear_off(self) -> None:
        """Clear the off state when heatpump turns back on."""
        if self._off_since is not None:
            off_duration = dt_util.utcnow() - self._off_since
            _LOGGER.info(
                f"Heatpump restarted after {off_duration.total_seconds() / 60:.1f} minutes off"
            )
            self._off_since = None
