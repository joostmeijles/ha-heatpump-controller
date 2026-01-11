"""Pure calculation functions for the heatpump controller.

This module contains stateless calculation functions that operate on temperature data.
"""

import logging
from typing import List, Tuple

_LOGGER = logging.getLogger(__name__)


def calculate_weighted_averages(
    temps: List[Tuple[float, float, float]]
) -> Tuple[float, float, float]:
    """
    Calculate weighted averages for current and target temperatures.
    
    Args:
        temps: List of tuples (current_temp, target_temp, weight)
        
    Returns:
        Tuple of (weighted_current_temp, weighted_target_temp, weighted_needed_temp)
        Returns (0, 0, 0) if total weight is zero.
    """
    total_weight = sum(weight for _, _, weight in temps)
    if total_weight == 0:
        return 0, 0, 0

    weighted_temp = sum(temp * weight for temp, _, weight in temps) / total_weight
    weighted_target = sum(target * weight for _, target, weight in temps) / total_weight

    # Calculate weighted needed temperatures
    weighted_needed_temp_values: List[float] = []
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
        f"Weighted temp: {weighted_temp:.3f}°C, weighted target: {weighted_target:.3f}°C, "
        f"average gap to target: {weighted_needed_temp:.3f}°C"
    )
    return weighted_temp, weighted_target, weighted_needed_temp


def calculate_num_rooms_below_target(
    temps: List[Tuple[float, float, float]]
) -> int:
    """
    Calculate number of rooms below their target temperatures.
    
    Args:
        temps: List of tuples (current_temp, target_temp, weight)
        
    Returns:
        Count of rooms where current_temp < target_temp
    """
    count = 0
    for temp, target, _ in temps:
        if temp < target:
            count += 1
    return count


def any_room_needs_heat(
    temps: List[Tuple[float, float, float]], threshold: float
) -> bool:
    """
    Return True if any room is below target by the specified threshold.
    
    Args:
        temps: List of tuples (current_temp, target_temp, weight)
        threshold: Minimum temperature difference required to need heat
        
    Returns:
        True if any room's (target - current) >= threshold
    """
    for current, target, _ in temps:
        diff = target - current
        if diff >= threshold:
            _LOGGER.debug(
                "Room below target: current=%.3f target=%.3f diff=%.3f ≥ %.3f",
                current,
                target,
                diff,
                threshold,
            )
            return True
    return False
