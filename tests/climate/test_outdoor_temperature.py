"""Tests for outdoor_temperature module."""

from unittest.mock import patch
from config.custom_components.heatpump_controller.climate.outdoor_temperature import (
    OutdoorTemperatureManager,
)


class TestOutdoorTemperatureManager:
    """Test the OutdoorTemperatureManager class."""

    def test_initialization(self, mock_hass, sample_outdoor_thresholds):
        """Test manager initialization."""
        manager = OutdoorTemperatureManager(
            mock_hass,
            "sensor.outdoor",
            "sensor.outdoor_fallback",
            sample_outdoor_thresholds,
        )
        
        assert manager.outdoor_sensor == "sensor.outdoor"
        assert manager.outdoor_sensor_fallback == "sensor.outdoor_fallback"
        assert manager.outdoor_thresholds == sample_outdoor_thresholds
        assert manager.outdoor_temp is None
        assert manager.active_outdoor_mapping is None

    def test_initialization_without_optional_params(self, mock_hass):
        """Test manager initialization without optional parameters."""
        manager = OutdoorTemperatureManager(mock_hass)
        
        assert manager.outdoor_sensor is None
        assert manager.outdoor_sensor_fallback is None
        assert manager.outdoor_thresholds == []


class TestGetOutdoorTemperature:
    """Test the get_outdoor_temperature method."""

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    def test_read_from_primary_sensor(self, mock_read_sensor, mock_hass):
        """Test reading from primary sensor successfully."""
        mock_read_sensor.return_value = 15.5
        manager = OutdoorTemperatureManager(mock_hass, "sensor.outdoor")
        
        temp = manager.get_outdoor_temperature()
        
        assert temp == 15.5
        assert manager.outdoor_temp == 15.5
        mock_read_sensor.assert_called_once_with(mock_hass, "sensor.outdoor", "Outdoor")

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    def test_fallback_to_secondary_sensor(self, mock_read_sensor, mock_hass):
        """Test falling back to secondary sensor when primary fails."""
        # Primary returns None, fallback returns 15.5
        mock_read_sensor.side_effect = [None, 15.5]
        manager = OutdoorTemperatureManager(
            mock_hass,
            "sensor.outdoor",
            "sensor.outdoor_fallback",
        )
        
        temp = manager.get_outdoor_temperature()
        
        assert temp == 15.5
        assert manager.outdoor_temp == 15.5
        assert mock_read_sensor.call_count == 2

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    def test_both_sensors_unavailable(self, mock_read_sensor, mock_hass):
        """Test when both sensors are unavailable."""
        mock_read_sensor.return_value = None
        manager = OutdoorTemperatureManager(
            mock_hass,
            "sensor.outdoor",
            "sensor.outdoor_fallback",
        )
        
        temp = manager.get_outdoor_temperature()
        
        assert temp is None
        assert manager.outdoor_temp is None

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    def test_no_fallback_sensor(self, mock_read_sensor, mock_hass):
        """Test when primary fails and no fallback is configured."""
        mock_read_sensor.return_value = None
        manager = OutdoorTemperatureManager(mock_hass, "sensor.outdoor")
        
        temp = manager.get_outdoor_temperature()
        
        assert temp is None
        assert manager.outdoor_temp is None
        mock_read_sensor.assert_called_once()


class TestMatchOutdoorThreshold:
    """Test the match_outdoor_threshold method."""

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    def test_match_first_range(self, mock_read_sensor, mock_hass, sample_outdoor_thresholds):
        """Test matching the first temperature range."""
        mock_read_sensor.return_value = 0.0  # In range [-10, 5)
        manager = OutdoorTemperatureManager(
            mock_hass,
            "sensor.outdoor",
            outdoor_thresholds=sample_outdoor_thresholds,
        )
        
        manager.match_outdoor_threshold()
        
        assert manager.active_outdoor_mapping is not None
        assert manager.active_outdoor_mapping["threshold_before_heat"] == 0.03
        assert manager.active_outdoor_mapping["threshold_before_off"] == 0.003

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    def test_match_middle_range(self, mock_read_sensor, mock_hass, sample_outdoor_thresholds):
        """Test matching a middle temperature range."""
        mock_read_sensor.return_value = 10.0  # In range [5, 15)
        manager = OutdoorTemperatureManager(
            mock_hass,
            "sensor.outdoor",
            outdoor_thresholds=sample_outdoor_thresholds,
        )
        
        manager.match_outdoor_threshold()
        
        assert manager.active_outdoor_mapping is not None
        assert manager.active_outdoor_mapping["threshold_before_heat"] == 0.07
        assert manager.active_outdoor_mapping["threshold_before_off"] == 0.007

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    def test_match_last_range(self, mock_read_sensor, mock_hass, sample_outdoor_thresholds):
        """Test matching the last temperature range with only min_temp."""
        mock_read_sensor.return_value = 20.0  # >= 15
        manager = OutdoorTemperatureManager(
            mock_hass,
            "sensor.outdoor",
            outdoor_thresholds=sample_outdoor_thresholds,
        )
        
        manager.match_outdoor_threshold()
        
        assert manager.active_outdoor_mapping is not None
        assert manager.active_outdoor_mapping["threshold_before_heat"] == 0.15
        assert manager.active_outdoor_mapping["threshold_before_off"] == 0.015

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    def test_match_boundary_inclusive(self, mock_read_sensor, mock_hass, sample_outdoor_thresholds):
        """Test that min_temp boundary is inclusive."""
        mock_read_sensor.return_value = 5.0  # Exactly at boundary
        manager = OutdoorTemperatureManager(
            mock_hass,
            "sensor.outdoor",
            outdoor_thresholds=sample_outdoor_thresholds,
        )
        
        manager.match_outdoor_threshold()
        
        # Should match second range [5, 15)
        assert manager.active_outdoor_mapping["threshold_before_heat"] == 0.07

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    def test_match_boundary_exclusive(self, mock_read_sensor, mock_hass, sample_outdoor_thresholds):
        """Test that max_temp boundary is exclusive."""
        mock_read_sensor.return_value = 15.0  # Exactly at boundary
        manager = OutdoorTemperatureManager(
            mock_hass,
            "sensor.outdoor",
            outdoor_thresholds=sample_outdoor_thresholds,
        )
        
        manager.match_outdoor_threshold()
        
        # Should match third range [15, ...)
        assert manager.active_outdoor_mapping["threshold_before_heat"] == 0.15

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    def test_no_matching_range(self, mock_read_sensor, mock_hass):
        """Test when no range matches."""
        mock_read_sensor.return_value = 10.0
        thresholds = [
            {"min_temp": -10, "max_temp": 0, "threshold_before_heat": 0.03, "threshold_before_off": 0.003},
            {"min_temp": 20, "max_temp": 30, "threshold_before_heat": 0.15, "threshold_before_off": 0.015},
        ]
        manager = OutdoorTemperatureManager(
            mock_hass,
            "sensor.outdoor",
            outdoor_thresholds=thresholds,
        )
        
        manager.match_outdoor_threshold()
        
        assert manager.active_outdoor_mapping is None

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    def test_fallback_mapping_no_limits(self, mock_read_sensor, mock_hass):
        """Test fallback mapping with no min/max specified."""
        mock_read_sensor.return_value = 100.0  # Any temperature
        thresholds = [
            {"threshold_before_heat": 0.1, "threshold_before_off": 0.01},
        ]
        manager = OutdoorTemperatureManager(
            mock_hass,
            "sensor.outdoor",
            outdoor_thresholds=thresholds,
        )
        
        manager.match_outdoor_threshold()
        
        assert manager.active_outdoor_mapping is not None
        assert manager.active_outdoor_mapping["threshold_before_heat"] == 0.1

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    def test_outdoor_temp_unavailable_clears_mapping(self, mock_read_sensor, mock_hass, sample_outdoor_thresholds):
        """Test that unavailable outdoor temp clears active mapping."""
        # First set a mapping
        mock_read_sensor.return_value = 10.0
        manager = OutdoorTemperatureManager(
            mock_hass,
            "sensor.outdoor",
            outdoor_thresholds=sample_outdoor_thresholds,
        )
        manager.match_outdoor_threshold()
        assert manager.active_outdoor_mapping is not None
        
        # Now make outdoor temp unavailable
        mock_read_sensor.return_value = None
        manager.match_outdoor_threshold()
        
        assert manager.active_outdoor_mapping is None

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    def test_no_redundant_logging_for_same_mapping(self, mock_read_sensor, mock_hass, sample_outdoor_thresholds):
        """Test that same mapping doesn't trigger redundant updates."""
        mock_read_sensor.return_value = 10.0
        manager = OutdoorTemperatureManager(
            mock_hass,
            "sensor.outdoor",
            outdoor_thresholds=sample_outdoor_thresholds,
        )
        
        # First call sets the mapping
        manager.match_outdoor_threshold()
        first_mapping = manager.active_outdoor_mapping
        
        # Second call with same temp should keep same mapping
        manager.match_outdoor_threshold()
        
        assert manager.active_outdoor_mapping is first_mapping


class TestOutdoorTemperatureManagerHelpers:
    """Test helper methods of OutdoorTemperatureManager."""

    def test_get_active_mapping(self, mock_hass):
        """Test get_active_mapping method."""
        manager = OutdoorTemperatureManager(mock_hass)
        assert manager.get_active_mapping() is None
        
        manager.active_outdoor_mapping = {"threshold_before_heat": 0.07}
        assert manager.get_active_mapping() == {"threshold_before_heat": 0.07}

    def test_clear_active_mapping(self, mock_hass):
        """Test clear_active_mapping method."""
        manager = OutdoorTemperatureManager(mock_hass)
        manager.active_outdoor_mapping = {"threshold_before_heat": 0.07}
        
        manager.clear_active_mapping()
        
        assert manager.active_outdoor_mapping is None

    def test_clear_already_none_mapping(self, mock_hass):
        """Test clearing when mapping is already None."""
        manager = OutdoorTemperatureManager(mock_hass)
        assert manager.active_outdoor_mapping is None
        
        # Should not raise any error
        manager.clear_active_mapping()
        
        assert manager.active_outdoor_mapping is None


class TestRateLimiting:
    """Test rate limiting for outdoor mapping switches."""

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    def test_first_mapping_applies_immediately(self, mock_read_sensor, mock_hass, sample_outdoor_thresholds):
        """Test that the first mapping applies immediately without rate limiting."""
        from datetime import timedelta
        
        mock_read_sensor.return_value = 0.0  # Matches first range [-10, 5)
        manager = OutdoorTemperatureManager(
            mock_hass,
            "sensor.outdoor",
            outdoor_thresholds=sample_outdoor_thresholds,
            mapping_switch_delay=timedelta(seconds=1),
        )
        
        manager.match_outdoor_threshold()
        
        assert manager.active_outdoor_mapping is not None
        assert manager.active_outdoor_mapping["threshold_before_heat"] == 0.03
        assert manager._last_mapping_change is not None

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.dt_util')
    def test_mapping_switch_suppressed_within_delay(self, mock_dt_util, mock_read_sensor, mock_hass, sample_outdoor_thresholds):
        """Test that mapping switches are suppressed within the rate limit delay."""
        from datetime import timedelta, datetime, timezone
        
        # Set up a fixed time progression
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt_util.utcnow.return_value = base_time
        
        # First apply a mapping at 0.0°C
        mock_read_sensor.return_value = 0.0  # Matches first range
        manager = OutdoorTemperatureManager(
            mock_hass,
            "sensor.outdoor",
            outdoor_thresholds=sample_outdoor_thresholds,
            mapping_switch_delay=timedelta(hours=1),
        )
        manager.match_outdoor_threshold()
        
        assert manager.active_outdoor_mapping["threshold_before_heat"] == 0.03
        
        # Try to switch to second range 30 minutes later (should be suppressed)
        mock_dt_util.utcnow.return_value = base_time + timedelta(minutes=30)
        mock_read_sensor.return_value = 10.0  # Would match second range
        manager.match_outdoor_threshold()
        
        # Should still be first mapping due to rate limit
        assert manager.active_outdoor_mapping["threshold_before_heat"] == 0.03

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.dt_util')
    def test_mapping_switch_succeeds_after_delay(self, mock_dt_util, mock_read_sensor, mock_hass, sample_outdoor_thresholds):
        """Test that mapping switches succeed after the rate limit delay has passed."""
        from datetime import timedelta, datetime, timezone
        
        # Set up a fixed time progression
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt_util.utcnow.return_value = base_time
        
        # First apply a mapping at 0.0°C
        mock_read_sensor.return_value = 0.0  # Matches first range
        manager = OutdoorTemperatureManager(
            mock_hass,
            "sensor.outdoor",
            outdoor_thresholds=sample_outdoor_thresholds,
            mapping_switch_delay=timedelta(hours=1),
        )
        manager.match_outdoor_threshold()
        
        assert manager.active_outdoor_mapping["threshold_before_heat"] == 0.03
        
        # Try to switch to second range 90 minutes later (should succeed)
        mock_dt_util.utcnow.return_value = base_time + timedelta(minutes=90)
        mock_read_sensor.return_value = 10.0  # Matches second range
        manager.match_outdoor_threshold()
        
        # Should be second mapping now
        assert manager.active_outdoor_mapping["threshold_before_heat"] == 0.07

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    def test_clearing_resets_rate_limit(self, mock_read_sensor, mock_hass, sample_outdoor_thresholds):
        """Test that clearing a mapping resets the rate limit timestamp."""
        from datetime import timedelta
        
        # First apply a mapping
        mock_read_sensor.return_value = 0.0  # Matches first range
        manager = OutdoorTemperatureManager(
            mock_hass,
            "sensor.outdoor",
            outdoor_thresholds=sample_outdoor_thresholds,
            mapping_switch_delay=timedelta(hours=1),
        )
        manager.match_outdoor_threshold()
        
        assert manager.active_outdoor_mapping is not None
        assert manager._last_mapping_change is not None
        
        # Clear due to unavailable sensor
        mock_read_sensor.return_value = None
        manager.match_outdoor_threshold()
        
        assert manager.active_outdoor_mapping is None
        assert manager._last_mapping_change is None
        
        # Immediately apply a new mapping (should succeed without rate limit)
        mock_read_sensor.return_value = 10.0  # Matches second range
        manager.match_outdoor_threshold()
        
        assert manager.active_outdoor_mapping is not None
        assert manager.active_outdoor_mapping["threshold_before_heat"] == 0.07

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    def test_clearing_when_no_mapping_matched_resets_rate_limit(self, mock_read_sensor, mock_hass):
        """Test that clearing when no mapping matches resets the rate limit timestamp."""
        from datetime import timedelta
        
        thresholds = [
            {"min_temp": -10, "max_temp": 0, "threshold_before_heat": 0.03, "threshold_before_off": 0.003},
        ]
        
        # First apply a mapping
        mock_read_sensor.return_value = -5.0  # Matches range
        manager = OutdoorTemperatureManager(
            mock_hass,
            "sensor.outdoor",
            outdoor_thresholds=thresholds,
            mapping_switch_delay=timedelta(hours=1),
        )
        manager.match_outdoor_threshold()
        
        assert manager.active_outdoor_mapping is not None
        
        # Temperature outside range - should clear and reset timestamp
        mock_read_sensor.return_value = 10.0  # No mapping matches
        manager.match_outdoor_threshold()
        
        assert manager.active_outdoor_mapping is None
        assert manager._last_mapping_change is None

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    def test_clear_active_mapping_resets_timestamp(self, mock_read_sensor, mock_hass, sample_outdoor_thresholds):
        """Test that clear_active_mapping() resets the rate limit timestamp."""
        from datetime import timedelta
        
        # First apply a mapping
        mock_read_sensor.return_value = 0.0
        manager = OutdoorTemperatureManager(
            mock_hass,
            "sensor.outdoor",
            outdoor_thresholds=sample_outdoor_thresholds,
            mapping_switch_delay=timedelta(hours=1),
        )
        manager.match_outdoor_threshold()
        
        assert manager.active_outdoor_mapping is not None
        assert manager._last_mapping_change is not None
        
        # Manually clear the mapping
        manager.clear_active_mapping()
        
        assert manager.active_outdoor_mapping is None
        assert manager._last_mapping_change is None

    @patch('config.custom_components.heatpump_controller.climate.outdoor_temperature.read_sensor_temperature')
    def test_same_mapping_does_not_update_timestamp(self, mock_read_sensor, mock_hass, sample_outdoor_thresholds):
        """Test that keeping the same mapping does not update the timestamp."""
        from datetime import timedelta
        
        # First apply a mapping
        mock_read_sensor.return_value = 0.0
        manager = OutdoorTemperatureManager(
            mock_hass,
            "sensor.outdoor",
            outdoor_thresholds=sample_outdoor_thresholds,
            mapping_switch_delay=timedelta(hours=1),
        )
        manager.match_outdoor_threshold()
        
        original_timestamp = manager._last_mapping_change
        
        # Call again with same temperature (same mapping)
        manager.match_outdoor_threshold()
        
        # Timestamp should not have changed
        assert manager._last_mapping_change == original_timestamp
