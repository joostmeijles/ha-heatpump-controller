"""Tests for the heatpump controller select entity."""

import pytest
from unittest.mock import Mock, AsyncMock
from homeassistant.core import State

from config.custom_components.heatpump_controller.select import HeatpumpAlgorithmSelect
from config.custom_components.heatpump_controller.const import ControlAlgorithm
from config.custom_components.heatpump_controller.climate import HeatpumpThermostat


@pytest.fixture
def mock_controller():
    """Create a mock controller."""
    controller = Mock(spec=HeatpumpThermostat)
    controller.algorithm = ControlAlgorithm.MANUAL
    controller.unique_id = "test_controller"
    controller.set_algorithm = Mock()
    return controller


@pytest.fixture
def select_entity(mock_controller):
    """Create a select entity."""
    return HeatpumpAlgorithmSelect(mock_controller)


@pytest.mark.asyncio
async def test_init(select_entity, mock_controller):
    """Test initialization."""
    assert select_entity._controller == mock_controller
    assert select_entity._attr_current_option == "Manual"
    assert select_entity._attr_unique_id == "test_controller_Algorithm"


def test_options(select_entity):
    """Test that options returns all algorithm labels."""
    expected_options = [
        "Manual",
        "Weighted Average",
        "Weighted Average with Outdoor Temp",
        "LWT Control",
    ]
    assert select_entity.options == expected_options


def test_current_option(select_entity, mock_controller):
    """Test current_option property."""
    mock_controller.algorithm = ControlAlgorithm.WEIGHTED_AVERAGE
    assert select_entity.current_option == "Weighted Average"


@pytest.mark.asyncio
async def test_async_select_option(select_entity, mock_controller):
    """Test selecting an option."""
    select_entity.async_write_ha_state = Mock()
    
    await select_entity.async_select_option("Weighted Average")
    
    mock_controller.set_algorithm.assert_called_once_with(ControlAlgorithm.WEIGHTED_AVERAGE)
    assert select_entity._attr_current_option == "Weighted Average"
    select_entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_added_to_hass_no_previous_state(select_entity, mock_controller):
    """Test async_added_to_hass when there is no previous state."""
    # Mock the async_get_last_state to return None
    select_entity.async_get_last_state = AsyncMock(return_value=None)
    
    # Call the method
    await select_entity.async_added_to_hass()
    
    # Controller set_algorithm should not be called when there's no previous state
    mock_controller.set_algorithm.assert_not_called()


@pytest.mark.asyncio
async def test_async_added_to_hass_with_previous_state(select_entity, mock_controller):
    """Test async_added_to_hass with a valid previous state."""
    # Create a mock state
    mock_state = Mock(spec=State)
    mock_state.state = "Weighted Average"
    
    # Mock the async_get_last_state to return the mock state
    select_entity.async_get_last_state = AsyncMock(return_value=mock_state)
    
    # Mock async_write_ha_state to avoid hass requirement in tests
    select_entity.async_write_ha_state = Mock()
    
    # Call the method
    await select_entity.async_added_to_hass()
    
    # Controller set_algorithm should be called with the restored algorithm
    mock_controller.set_algorithm.assert_called_once_with(ControlAlgorithm.WEIGHTED_AVERAGE)
    assert select_entity._attr_current_option == "Weighted Average"
    # Verify state was written back
    select_entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_added_to_hass_with_outdoor_temp_algorithm(select_entity, mock_controller):
    """Test async_added_to_hass with outdoor temp algorithm."""
    # Create a mock state with the outdoor temp algorithm
    mock_state = Mock(spec=State)
    mock_state.state = "Weighted Average with Outdoor Temp"
    
    # Mock the async_get_last_state to return the mock state
    select_entity.async_get_last_state = AsyncMock(return_value=mock_state)
    
    # Mock async_write_ha_state to avoid hass requirement in tests
    select_entity.async_write_ha_state = Mock()
    
    # Call the method
    await select_entity.async_added_to_hass()
    
    # Controller set_algorithm should be called with the outdoor temp algorithm
    mock_controller.set_algorithm.assert_called_once_with(
        ControlAlgorithm.WEIGHTED_AVERAGE_OUTDOOR_TEMP
    )
    assert select_entity._attr_current_option == "Weighted Average with Outdoor Temp"
    # Verify state was written back
    select_entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_added_to_hass_with_invalid_state(select_entity, mock_controller):
    """Test async_added_to_hass with an invalid previous state."""
    # Create a mock state with an invalid option
    mock_state = Mock(spec=State)
    mock_state.state = "Invalid Algorithm"
    
    # Mock the async_get_last_state to return the mock state
    select_entity.async_get_last_state = AsyncMock(return_value=mock_state)
    
    # Call the method
    await select_entity.async_added_to_hass()
    
    # Controller set_algorithm should not be called with invalid state
    mock_controller.set_algorithm.assert_not_called()
