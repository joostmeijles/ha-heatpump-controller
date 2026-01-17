"""Tests for HeatpumpThermostat algorithm persistence."""

import pytest
from unittest.mock import Mock, patch
from config.custom_components.heatpump_controller.climate import HeatpumpThermostat, AlgorithmStoredData
from config.custom_components.heatpump_controller.const import ControlAlgorithm


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.states = Mock()
    hass.services = Mock()
    hass.async_create_task = Mock(side_effect=lambda coro: None)
    return hass


@pytest.fixture
def sample_rooms():
    """Sample room configurations."""
    return [
        {"sensor": "climate.living_room", "weight": 1.0},
        {"sensor": "climate.bedroom", "weight": 1.5},
    ]


class TestAlgorithmPersistence:
    """Test algorithm persistence in HeatpumpThermostat."""

    @pytest.mark.asyncio
    async def test_restore_algorithm_weighted_average(self, mock_hass, sample_rooms):
        # Create thermostat instance
        thermostat = HeatpumpThermostat(
            mock_hass,
            sample_rooms,
            "switch.heatpump",
            0.07,
            0.007,
            0.3,
        )

        # Mock last extra data with weighted_average algorithm
        extra_data = AlgorithmStoredData("weighted_average")

        # Patch async_get_last_extra_data to return our mocked data
        with patch.object(thermostat, "async_get_last_extra_data", return_value=extra_data):
            with patch("config.custom_components.heatpump_controller.climate.async_track_time_interval"):
                await thermostat.async_added_to_hass()

        # Verify algorithm was restored
        assert thermostat.algorithm == ControlAlgorithm.WEIGHTED_AVERAGE

    @pytest.mark.asyncio
    async def test_restore_algorithm_weighted_average_outdoor_temp(self, mock_hass, sample_rooms):
        # Create thermostat instance
        thermostat = HeatpumpThermostat(
            mock_hass,
            sample_rooms,
            "switch.heatpump",
            0.07,
            0.007,
            0.3,
        )

        # Mock last extra data with weighted_average_outdoor_temp algorithm
        extra_data = AlgorithmStoredData("weighted_average_outdoor_temp")

        # Patch async_get_last_extra_data to return our mocked data
        with patch.object(thermostat, "async_get_last_extra_data", return_value=extra_data):
            with patch("config.custom_components.heatpump_controller.climate.async_track_time_interval"):
                await thermostat.async_added_to_hass()

        # Verify algorithm was restored
        assert thermostat.algorithm == ControlAlgorithm.WEIGHTED_AVERAGE_OUTDOOR_TEMP

    @pytest.mark.asyncio
    async def test_restore_algorithm_manual(self, mock_hass, sample_rooms):
        # Create thermostat instance
        thermostat = HeatpumpThermostat(
            mock_hass,
            sample_rooms,
            "switch.heatpump",
            0.07,
            0.007,
            0.3,
        )

        # Mock last extra data with manual algorithm
        extra_data = AlgorithmStoredData("manual")

        # Patch async_get_last_extra_data to return our mocked data
        with patch.object(thermostat, "async_get_last_extra_data", return_value=extra_data):
            with patch("config.custom_components.heatpump_controller.climate.async_track_time_interval"):
                await thermostat.async_added_to_hass()

        # Verify algorithm was restored
        assert thermostat.algorithm == ControlAlgorithm.MANUAL

    @pytest.mark.asyncio
    async def test_default_algorithm_no_previous_data(self, mock_hass, sample_rooms):
        # Create thermostat instance
        thermostat = HeatpumpThermostat(
            mock_hass,
            sample_rooms,
            "switch.heatpump",
            0.07,
            0.007,
            0.3,
        )

        # Patch async_get_last_extra_data to return None (no previous data)
        with patch.object(thermostat, "async_get_last_extra_data", return_value=None):
            with patch("config.custom_components.heatpump_controller.climate.async_track_time_interval"):
                await thermostat.async_added_to_hass()

        # Verify default algorithm is used (MANUAL)
        assert thermostat.algorithm == ControlAlgorithm.MANUAL

    @pytest.mark.asyncio
    async def test_invalid_algorithm_value(self, mock_hass, sample_rooms):
        # Create thermostat instance
        thermostat = HeatpumpThermostat(
            mock_hass,
            sample_rooms,
            "switch.heatpump",
            0.07,
            0.007,
            0.3,
        )

        # Mock last extra data with invalid algorithm
        extra_data = AlgorithmStoredData("invalid_algo")

        # Patch async_get_last_extra_data to return data with invalid algorithm
        with patch.object(thermostat, "async_get_last_extra_data", return_value=extra_data):
            with patch("config.custom_components.heatpump_controller.climate.async_track_time_interval"):
                await thermostat.async_added_to_hass()

        # Verify default algorithm is used when invalid value encountered
        assert thermostat.algorithm == ControlAlgorithm.MANUAL

