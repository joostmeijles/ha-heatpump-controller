"""Tests for calculations module."""

import pytest
from config.custom_components.heatpump_controller.climate.calculations import (
    calculate_weighted_averages,
    calculate_num_rooms_below_target,
    any_room_needs_heat,
)


@pytest.fixture
def sample_room_temps():
    """Sample room temperature data for testing."""
    return [
        (20.0, 22.0, 1.0),  # Room 1: 20°C current, 22°C target, weight 1.0
        (19.0, 21.0, 1.5),  # Room 2: 19°C current, 21°C target, weight 1.5
        (21.0, 22.0, 1.0),  # Room 3: 21°C current, 22°C target, weight 1.0
    ]


class TestCalculateWeightedAverages:
    """Test the calculate_weighted_averages function."""

    def test_basic_weighted_averages(self, sample_room_temps):
        """Test weighted averages with typical room data."""
        avg_temp, avg_target, avg_needed = calculate_weighted_averages(sample_room_temps)
        
        # Weighted average temp: (20*1.0 + 19*1.5 + 21*1.0) / 3.5 = 69.5 / 3.5 = 19.857
        assert abs(avg_temp - 19.857) < 0.01
        
        # Weighted average target: (22*1.0 + 21*1.5 + 22*1.0) / 3.5 = 75.5 / 3.5 = 21.571
        assert abs(avg_target - 21.571) < 0.01
        
        # Weighted needed: ((2*1.0) + (2*1.5) + (1*1.0)) / 3.5 = 6.0 / 3.5 = 1.714
        assert abs(avg_needed - 1.714) < 0.01

    def test_empty_list(self):
        """Test with empty temperature list."""
        avg_temp, avg_target, avg_needed = calculate_weighted_averages([])
        assert avg_temp == 0
        assert avg_target == 0
        assert avg_needed == 0

    def test_zero_weights(self):
        """Test with zero total weight."""
        temps = [(20.0, 22.0, 0.0), (19.0, 21.0, 0.0)]
        avg_temp, avg_target, avg_needed = calculate_weighted_averages(temps)
        assert avg_temp == 0
        assert avg_target == 0
        assert avg_needed == 0

    def test_single_room(self):
        """Test with a single room."""
        temps = [(20.0, 22.0, 1.0)]
        avg_temp, avg_target, avg_needed = calculate_weighted_averages(temps)
        assert avg_temp == 20.0
        assert avg_target == 22.0
        assert avg_needed == 2.0

    def test_room_above_target(self):
        """Test that rooms above target don't contribute negatively to needed temp."""
        temps = [(23.0, 22.0, 1.0), (20.0, 22.0, 1.0)]
        avg_temp, avg_target, avg_needed = calculate_weighted_averages(temps)
        # Room 1 is above target, should contribute 0 to needed
        # Room 2 needs 2 degrees
        # Average needed: (0*1.0 + 2*1.0) / 2.0 = 1.0
        assert avg_needed == 1.0

    def test_all_rooms_at_target(self):
        """Test when all rooms are at target temperature."""
        temps = [(22.0, 22.0, 1.0), (21.0, 21.0, 1.5)]
        avg_temp, avg_target, avg_needed = calculate_weighted_averages(temps)
        assert avg_needed == 0.0

    def test_different_weights(self):
        """Test that weights properly affect the average."""
        # Room 1: very important (weight 10), needs heat
        # Room 2: less important (weight 1), at target
        temps = [(18.0, 22.0, 10.0), (22.0, 22.0, 1.0)]
        avg_temp, avg_target, avg_needed = calculate_weighted_averages(temps)
        # Needed: (4*10 + 0*1) / 11 = 40/11 = 3.636
        assert abs(avg_needed - 3.636) < 0.01


class TestCalculateNumRoomsBelowTarget:
    """Test the calculate_num_rooms_below_target function."""

    def test_all_rooms_below_target(self):
        """Test when all rooms are below target."""
        temps = [(20.0, 22.0, 1.0), (19.0, 21.0, 1.5), (21.0, 22.0, 1.0)]
        count = calculate_num_rooms_below_target(temps)
        assert count == 3

    def test_no_rooms_below_target(self):
        """Test when no rooms are below target."""
        temps = [(22.0, 22.0, 1.0), (22.0, 21.0, 1.5), (23.0, 22.0, 1.0)]
        count = calculate_num_rooms_below_target(temps)
        assert count == 0

    def test_some_rooms_below_target(self):
        """Test when some rooms are below target."""
        temps = [(20.0, 22.0, 1.0), (22.0, 21.0, 1.5), (21.0, 22.0, 1.0)]
        count = calculate_num_rooms_below_target(temps)
        assert count == 2

    def test_empty_list(self):
        """Test with empty list."""
        count = calculate_num_rooms_below_target([])
        assert count == 0

    def test_single_room_below(self):
        """Test with single room below target."""
        temps = [(20.0, 22.0, 1.0)]
        count = calculate_num_rooms_below_target(temps)
        assert count == 1

    def test_single_room_at_target(self):
        """Test with single room at target."""
        temps = [(22.0, 22.0, 1.0)]
        count = calculate_num_rooms_below_target(temps)
        assert count == 0


class TestAnyRoomNeedsHeat:
    """Test the any_room_needs_heat function."""

    def test_one_room_exceeds_threshold(self):
        """Test when one room exceeds the threshold."""
        temps = [(20.0, 22.5, 1.0), (21.5, 22.0, 1.5), (22.0, 22.0, 1.0)]
        result = any_room_needs_heat(temps, threshold=2.0)
        assert result is True

    def test_no_room_exceeds_threshold(self):
        """Test when no room exceeds the threshold."""
        temps = [(21.0, 22.0, 1.0), (21.5, 22.0, 1.5), (22.0, 22.0, 1.0)]
        result = any_room_needs_heat(temps, threshold=2.0)
        assert result is False

    def test_exact_threshold_match(self):
        """Test when a room exactly matches the threshold."""
        temps = [(20.0, 22.0, 1.0), (21.5, 22.0, 1.5)]
        result = any_room_needs_heat(temps, threshold=2.0)
        # diff = 2.0, threshold = 2.0, should be True (>=)
        assert result is True

    def test_just_below_threshold(self):
        """Test when all rooms are just below the threshold."""
        temps = [(20.1, 22.0, 1.0), (21.5, 22.0, 1.5)]
        result = any_room_needs_heat(temps, threshold=2.0)
        # diff = 1.9 < 2.0
        assert result is False

    def test_zero_threshold(self):
        """Test with zero threshold."""
        temps = [(21.9, 22.0, 1.0), (22.0, 22.0, 1.5)]
        result = any_room_needs_heat(temps, threshold=0.0)
        # First room diff = 0.1 >= 0.0
        assert result is True

    def test_all_rooms_above_target(self):
        """Test when all rooms are above target temperature."""
        temps = [(23.0, 22.0, 1.0), (23.5, 22.0, 1.5)]
        result = any_room_needs_heat(temps, threshold=2.0)
        assert result is False

    def test_empty_list(self):
        """Test with empty list."""
        result = any_room_needs_heat([], threshold=2.0)
        assert result is False

    def test_high_threshold(self):
        """Test with very high threshold."""
        temps = [(20.0, 22.0, 1.0), (19.0, 21.0, 1.5)]
        result = any_room_needs_heat(temps, threshold=5.0)
        # Max diff is 2.0, threshold is 5.0
        assert result is False
