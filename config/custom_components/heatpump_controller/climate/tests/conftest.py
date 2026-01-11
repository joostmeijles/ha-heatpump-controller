"""Pytest configuration and fixtures for climate package tests."""

import pytest
from unittest.mock import Mock
from typing import Any, Dict, Optional


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.states = Mock()
    hass.services = Mock()
    return hass


@pytest.fixture
def mock_state():
    """Create a mock state factory."""
    def _create_state(entity_id: str, state: str, attributes: Optional[Dict[str, Any]] = None):
        mock_state = Mock()
        mock_state.entity_id = entity_id
        mock_state.state = state
        mock_state.attributes = attributes or {}
        return mock_state
    return _create_state


@pytest.fixture
def sample_room_configs():
    """Sample room configurations."""
    return [
        {"sensor": "climate.living_room", "weight": 1.0},
        {"sensor": "climate.bedroom", "weight": 1.5},
        {"sensor": "climate.office", "weight": 1.0},
    ]


@pytest.fixture
def sample_outdoor_thresholds():
    """Sample outdoor threshold configurations."""
    return [
        {
            "min_temp": -10,
            "max_temp": 5,
            "threshold_before_heat": 0.03,
            "threshold_before_off": 0.003,
        },
        {
            "min_temp": 5,
            "max_temp": 15,
            "threshold_before_heat": 0.07,
            "threshold_before_off": 0.007,
        },
        {
            "min_temp": 15,
            "threshold_before_heat": 0.15,
            "threshold_before_off": 0.015,
        },
    ]
