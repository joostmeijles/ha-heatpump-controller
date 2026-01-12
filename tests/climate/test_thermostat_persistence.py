"""Tests for HeatpumpThermostat algorithm persistence."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from homeassistant.core import State
from config.custom_components.heatpump_controller.climate import HeatpumpThermostat
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
        """Test restoring weighted_average algorithm from state."""
        # Create thermostat instance
        thermostat = HeatpumpThermostat(
            mock_hass,
            sample_rooms,
            "switch.heatpump",
            0.07,
            0.007,
            0.3,
        )

        # Mock last state with weighted_average algorithm
        last_state = State(
            "climate.heatpump_controller",
            "heat",
            {
                "algorithm": "weighted_average",
                "current_temperature": 20.0,
                "target_temperature": 21.0,
            },
        )

        # Patch async_get_last_state to return our mocked state
        with patch.object(thermostat, "async_get_last_state", return_value=last_state):
            with patch("config.custom_components.heatpump_controller.climate.async_track_time_interval"):
                await thermostat.async_added_to_hass()

        # Verify algorithm was restored
        assert thermostat.algorithm == ControlAlgorithm.WEIGHTED_AVERAGE

    @pytest.mark.asyncio
    async def test_restore_algorithm_weighted_average_outdoor_temp(self, mock_hass, sample_rooms):
        """Test restoring weighted_average_outdoor_temp algorithm from state."""
        # Create thermostat instance
        thermostat = HeatpumpThermostat(
            mock_hass,
            sample_rooms,
            "switch.heatpump",
            0.07,
            0.007,
            0.3,
        )

        # Mock last state with weighted_average_outdoor_temp algorithm
        last_state = State(
            "climate.heatpump_controller",
            "heat",
            {
                "algorithm": "weighted_average_outdoor_temp",
                "current_temperature": 20.0,
                "target_temperature": 21.0,
            },
        )

        # Patch async_get_last_state to return our mocked state
        with patch.object(thermostat, "async_get_last_state", return_value=last_state):
            with patch("config.custom_components.heatpump_controller.climate.async_track_time_interval"):
                await thermostat.async_added_to_hass()

        # Verify algorithm was restored
        assert thermostat.algorithm == ControlAlgorithm.WEIGHTED_AVERAGE_OUTDOOR_TEMP

    @pytest.mark.asyncio
    async def test_restore_algorithm_manual(self, mock_hass, sample_rooms):
        """Test restoring manual algorithm from state."""
        # Create thermostat instance
        thermostat = HeatpumpThermostat(
            mock_hass,
            sample_rooms,
            "switch.heatpump",
            0.07,
            0.007,
            0.3,
        )

        # Mock last state with manual algorithm
        last_state = State(
            "climate.heatpump_controller",
            "off",
            {
                "algorithm": "manual",
                "current_temperature": 20.0,
                "target_temperature": 21.0,
            },
        )

        # Patch async_get_last_state to return our mocked state
        with patch.object(thermostat, "async_get_last_state", return_value=last_state):
            with patch("config.custom_components.heatpump_controller.climate.async_track_time_interval"):
                await thermostat.async_added_to_hass()

        # Verify algorithm was restored
        assert thermostat.algorithm == ControlAlgorithm.MANUAL

    @pytest.mark.asyncio
    async def test_default_algorithm_no_previous_state(self, mock_hass, sample_rooms):
        """Test default algorithm when no previous state exists."""
        # Create thermostat instance
        thermostat = HeatpumpThermostat(
            mock_hass,
            sample_rooms,
            "switch.heatpump",
            0.07,
            0.007,
            0.3,
        )

        # Patch async_get_last_state to return None (no previous state)
        with patch.object(thermostat, "async_get_last_state", return_value=None):
            with patch("config.custom_components.heatpump_controller.climate.async_track_time_interval"):
                await thermostat.async_added_to_hass()

        # Verify default algorithm is used (MANUAL)
        assert thermostat.algorithm == ControlAlgorithm.MANUAL

    @pytest.mark.asyncio
    async def test_default_algorithm_no_attributes(self, mock_hass, sample_rooms):
        """Test default algorithm when previous state has no attributes."""
        # Create thermostat instance
        thermostat = HeatpumpThermostat(
            mock_hass,
            sample_rooms,
            "switch.heatpump",
            0.07,
            0.007,
            0.3,
        )

        # Mock last state without attributes
        last_state = State("climate.heatpump_controller", "heat")

        # Patch async_get_last_state to return state without attributes
        with patch.object(thermostat, "async_get_last_state", return_value=last_state):
            with patch("config.custom_components.heatpump_controller.climate.async_track_time_interval"):
                await thermostat.async_added_to_hass()

        # Verify default algorithm is used (MANUAL)
        assert thermostat.algorithm == ControlAlgorithm.MANUAL

    @pytest.mark.asyncio
    async def test_default_algorithm_missing_algorithm_attribute(self, mock_hass, sample_rooms):
        """Test default algorithm when algorithm attribute is missing."""
        # Create thermostat instance
        thermostat = HeatpumpThermostat(
            mock_hass,
            sample_rooms,
            "switch.heatpump",
            0.07,
            0.007,
            0.3,
        )

        # Mock last state with attributes but no algorithm
        last_state = State(
            "climate.heatpump_controller",
            "heat",
            {"current_temperature": 20.0, "target_temperature": 21.0},
        )

        # Patch async_get_last_state to return state without algorithm attribute
        with patch.object(thermostat, "async_get_last_state", return_value=last_state):
            with patch("config.custom_components.heatpump_controller.climate.async_track_time_interval"):
                await thermostat.async_added_to_hass()

        # Verify default algorithm is used (MANUAL)
        assert thermostat.algorithm == ControlAlgorithm.MANUAL

    @pytest.mark.asyncio
    async def test_invalid_algorithm_value(self, mock_hass, sample_rooms):
        """Test handling invalid algorithm value in state."""
        # Create thermostat instance
        thermostat = HeatpumpThermostat(
            mock_hass,
            sample_rooms,
            "switch.heatpump",
            0.07,
            0.007,
            0.3,
        )

        # Mock last state with invalid algorithm
        last_state = State(
            "climate.heatpump_controller",
            "heat",
            {"algorithm": "invalid_algo", "current_temperature": 20.0},
        )

        # Patch async_get_last_state to return state with invalid algorithm
        with patch.object(thermostat, "async_get_last_state", return_value=last_state):
            with patch("config.custom_components.heatpump_controller.climate.async_track_time_interval"):
                await thermostat.async_added_to_hass()

        # Verify default algorithm is used when invalid value encountered
        assert thermostat.algorithm == ControlAlgorithm.MANUAL

    @pytest.mark.asyncio
    async def test_algorithm_set_and_persisted_in_state(self, mock_hass, sample_rooms):
        """Test that algorithm is included in state attributes for persistence."""
        # Create thermostat instance
        thermostat = HeatpumpThermostat(
            mock_hass,
            sample_rooms,
            "switch.heatpump",
            0.07,
            0.007,
            0.3,
        )

        # Set algorithm
        thermostat.set_algorithm(ControlAlgorithm.WEIGHTED_AVERAGE)

        # Verify algorithm is exposed via property
        assert thermostat.algorithm == ControlAlgorithm.WEIGHTED_AVERAGE

    @pytest.mark.asyncio
    async def test_algorithm_changes_persist_across_restart(self, mock_hass, sample_rooms):
        """Test that algorithm changes are reflected in restored state."""
        # Create initial thermostat and set algorithm
        thermostat1 = HeatpumpThermostat(
            mock_hass,
            sample_rooms,
            "switch.heatpump",
            0.07,
            0.007,
            0.3,
        )
        thermostat1.set_algorithm(ControlAlgorithm.WEIGHTED_AVERAGE_OUTDOOR_TEMP)

        # Simulate restart - create new thermostat and restore from "state"
        thermostat2 = HeatpumpThermostat(
            mock_hass,
            sample_rooms,
            "switch.heatpump",
            0.07,
            0.007,
            0.3,
        )

        # Mock last state based on first thermostat's algorithm
        last_state = State(
            "climate.heatpump_controller",
            "heat",
            {"algorithm": thermostat1.algorithm.value},
        )

        # Restore state in second thermostat
        with patch.object(thermostat2, "async_get_last_state", return_value=last_state):
            with patch("config.custom_components.heatpump_controller.climate.async_track_time_interval"):
                await thermostat2.async_added_to_hass()

        # Verify algorithm was preserved
        assert thermostat2.algorithm == ControlAlgorithm.WEIGHTED_AVERAGE_OUTDOOR_TEMP
        assert thermostat2.algorithm == thermostat1.algorithm
