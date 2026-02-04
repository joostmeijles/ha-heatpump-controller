"""Tests for lwt_controller module."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from config.custom_components.heatpump_controller.climate.lwt_controller import LWTController


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.states.get = MagicMock()
    hass.services.async_call = AsyncMock()
    return hass


@pytest.fixture
def lwt_controller(mock_hass):
    """Create an LWT controller instance with default config."""
    return LWTController(
        hass=mock_hass,
        lwt_deviation_entity="number.lwt_offset",
        lwt_actual_sensor="sensor.lwt_actual",
        lwt_setpoint_sensor="sensor.lwt_setpoint",
        max_room_setpoint=22.0,
        lwt_deviation_min=-10.0,
        lwt_deviation_max=10.0,
        min_off_time_minutes=30,
        lwt_overcapacity_threshold=1.0,
        lwt_overcapacity_duration_minutes=60,
    )


class TestLWTControllerInitialization:
    """Test LWTController initialization."""

    def test_initialization(self, lwt_controller):
        """Test controller initialization with basic parameters."""
        assert lwt_controller._max_room_setpoint == 22.0
        assert lwt_controller._lwt_deviation_min == -10.0
        assert lwt_controller._lwt_deviation_max == 10.0
        assert lwt_controller._min_off_time_minutes == 30
        assert lwt_controller._lwt_overcapacity_threshold == 1.0
        assert lwt_controller._lwt_overcapacity_duration_minutes == 60
        assert not lwt_controller.is_active
        assert lwt_controller.current_deviation == 0.0


class TestActivateDeactivate:
    """Test activation and deactivation of LWT mode."""

    @pytest.mark.asyncio
    async def test_activate_saves_and_overrides_setpoints(self, lwt_controller, mock_hass):
        """Test that activate saves original setpoints and sets to max."""
        # Setup mock room states
        room1_state = MagicMock()
        room1_state.attributes = {"temperature": 20.0}
        room2_state = MagicMock()
        room2_state.attributes = {"temperature": 21.0}
        
        mock_hass.states.get.side_effect = lambda entity_id: {
            "climate.room1": room1_state,
            "climate.room2": room2_state,
        }.get(entity_id)
        
        rooms = [
            {"sensor": "climate.room1"},
            {"sensor": "climate.room2"},
        ]
        
        await lwt_controller.activate(rooms)
        
        # Check that original setpoints were saved
        assert lwt_controller._original_setpoints["climate.room1"] == 20.0
        assert lwt_controller._original_setpoints["climate.room2"] == 21.0
        
        # Check that setpoints were set to max
        assert mock_hass.services.async_call.call_count == 2
        calls = mock_hass.services.async_call.call_args_list
        assert calls[0][0][0] == "climate"
        assert calls[0][0][1] == "set_temperature"
        assert calls[0][0][2] == {"entity_id": "climate.room1", "temperature": 22.0}
        assert calls[1][0][0] == "climate"
        assert calls[1][0][1] == "set_temperature"
        assert calls[1][0][2] == {"entity_id": "climate.room2", "temperature": 22.0}
        
        # Check active state
        assert lwt_controller.is_active

    @pytest.mark.asyncio
    async def test_deactivate_restores_setpoints(self, lwt_controller, mock_hass):
        """Test that deactivate restores original setpoints."""
        # Set up saved setpoints
        lwt_controller._is_active = True
        lwt_controller._original_setpoints = {
            "climate.room1": 20.0,
            "climate.room2": 21.0,
        }
        
        rooms = [
            {"sensor": "climate.room1"},
            {"sensor": "climate.room2"},
        ]
        
        await lwt_controller.deactivate(rooms)
        
        # Check that setpoints were restored
        assert mock_hass.services.async_call.call_count == 2
        calls = mock_hass.services.async_call.call_args_list
        assert calls[0][0][0] == "climate"
        assert calls[0][0][1] == "set_temperature"
        assert calls[0][0][2] == {"entity_id": "climate.room1", "temperature": 20.0}
        assert calls[1][0][0] == "climate"
        assert calls[1][0][1] == "set_temperature"
        assert calls[1][0][2] == {"entity_id": "climate.room2", "temperature": 21.0}
        
        # Check that state was cleared
        assert not lwt_controller.is_active
        assert len(lwt_controller._original_setpoints) == 0


class TestOvercapacityDetection:
    """Test overcapacity detection logic."""

    @patch('config.custom_components.heatpump_controller.climate.lwt_controller.dt_util')
    def test_overcapacity_not_met_initially(self, mock_dt_util, lwt_controller, mock_hass):
        """Test that overcapacity is not met when condition just started."""
        now = datetime(2024, 1, 1, 12, 0, 0)
        mock_dt_util.utcnow.return_value = now
        
        # Setup LWT sensors - actual exceeds setpoint by threshold
        lwt_actual_state = MagicMock()
        lwt_actual_state.state = "45.0"
        lwt_setpoint_state = MagicMock()
        lwt_setpoint_state.state = "43.0"
        
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.lwt_actual": lwt_actual_state,
            "sensor.lwt_setpoint": lwt_setpoint_state,
        }.get(entity_id)
        
        # First check - should not be overcapacity yet
        assert not lwt_controller.is_overcapacity
        assert lwt_controller._overcapacity_start is not None

    @patch('config.custom_components.heatpump_controller.climate.lwt_controller.dt_util')
    def test_overcapacity_met_after_duration(self, mock_dt_util, lwt_controller, mock_hass):
        """Test that overcapacity is met after sustained duration."""
        now = datetime(2024, 1, 1, 12, 0, 0)
        mock_dt_util.utcnow.return_value = now
        
        # Setup LWT sensors
        lwt_actual_state = MagicMock()
        lwt_actual_state.state = "45.0"
        lwt_setpoint_state = MagicMock()
        lwt_setpoint_state.state = "43.0"
        
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.lwt_actual": lwt_actual_state,
            "sensor.lwt_setpoint": lwt_setpoint_state,
        }.get(entity_id)
        
        # First check - starts the timer
        assert not lwt_controller.is_overcapacity
        
        # Move time forward by 61 minutes
        mock_dt_util.utcnow.return_value = now + timedelta(minutes=61)
        
        # Should now be overcapacity
        assert lwt_controller.is_overcapacity

    @patch('config.custom_components.heatpump_controller.climate.lwt_controller.dt_util')
    def test_overcapacity_resets_when_condition_ends(self, mock_dt_util, lwt_controller, mock_hass):
        """Test that overcapacity timer resets when condition ends."""
        now = datetime(2024, 1, 1, 12, 0, 0)
        mock_dt_util.utcnow.return_value = now
        
        # Setup LWT sensors - initially overcapacity condition
        lwt_actual_state = MagicMock()
        lwt_actual_state.state = "45.0"
        lwt_setpoint_state = MagicMock()
        lwt_setpoint_state.state = "43.0"
        
        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.lwt_actual": lwt_actual_state,
            "sensor.lwt_setpoint": lwt_setpoint_state,
        }.get(entity_id)
        
        # Start overcapacity condition
        assert not lwt_controller.is_overcapacity
        assert lwt_controller._overcapacity_start is not None
        
        # Move time forward
        mock_dt_util.utcnow.return_value = now + timedelta(minutes=30)
        
        # Change condition - no longer overcapacity
        lwt_actual_state.state = "42.0"
        
        # Should reset timer
        assert not lwt_controller.is_overcapacity
        assert lwt_controller._overcapacity_start is None


class TestMinimumOffTime:
    """Test minimum off time enforcement."""

    @patch('config.custom_components.heatpump_controller.climate.lwt_controller.dt_util')
    def test_can_restart_when_not_off(self, mock_dt_util, lwt_controller):
        """Test that restart is allowed when not off."""
        assert lwt_controller.can_restart()

    @patch('config.custom_components.heatpump_controller.climate.lwt_controller.dt_util')
    def test_cannot_restart_during_min_off_time(self, mock_dt_util, lwt_controller):
        """Test that restart is blocked during minimum off time."""
        now = datetime(2024, 1, 1, 12, 0, 0)
        mock_dt_util.utcnow.return_value = now
        
        lwt_controller.mark_off()
        
        # Try to restart after 15 minutes (min is 30)
        mock_dt_util.utcnow.return_value = now + timedelta(minutes=15)
        assert not lwt_controller.can_restart()

    @patch('config.custom_components.heatpump_controller.climate.lwt_controller.dt_util')
    def test_can_restart_after_min_off_time_and_trending_down(self, mock_dt_util, lwt_controller):
        """Test that restart is allowed after min off time with downward trend."""
        now = datetime(2024, 1, 1, 12, 0, 0)
        mock_dt_util.utcnow.return_value = now
        
        # Mark as off first
        lwt_controller.mark_off()
        
        # Record decreasing temperature trend
        for i in range(10):
            mock_dt_util.utcnow.return_value = now + timedelta(minutes=i * 3)
            lwt_controller.record_temperature(22.0 - i * 0.1)
        
        # Try to restart after 35 minutes (min is 30)
        mock_dt_util.utcnow.return_value = now + timedelta(minutes=35)
        assert lwt_controller.can_restart()

    def test_off_remaining_minutes(self, lwt_controller):
        """Test off remaining minutes calculation."""
        # Not off
        assert lwt_controller.off_remaining_minutes is None
        
        # Just turned off
        with patch('config.custom_components.heatpump_controller.climate.lwt_controller.dt_util') as mock_dt_util:
            now = datetime(2024, 1, 1, 12, 0, 0)
            mock_dt_util.utcnow.return_value = now
            
            lwt_controller.mark_off()
            
            # 10 minutes later
            mock_dt_util.utcnow.return_value = now + timedelta(minutes=10)
            remaining = lwt_controller.off_remaining_minutes
            assert remaining is not None
            assert abs(remaining - 20.0) < 0.1  # Should be ~20 minutes remaining


class TestTemperatureTrend:
    """Test temperature trend calculation."""

    @patch('config.custom_components.heatpump_controller.climate.lwt_controller.dt_util')
    def test_trend_down_detected(self, mock_dt_util, lwt_controller):
        """Test that downward trend is detected."""
        now = datetime(2024, 1, 1, 12, 0, 0)
        mock_dt_util.utcnow.return_value = now
        
        # Record decreasing temperatures
        for i in range(10):
            lwt_controller.record_temperature(22.0 - i * 0.05)
            mock_dt_util.utcnow.return_value = now + timedelta(minutes=i * 3)
        
        assert lwt_controller._is_temp_trending_down()

    @patch('config.custom_components.heatpump_controller.climate.lwt_controller.dt_util')
    def test_trend_up_detected(self, mock_dt_util, lwt_controller):
        """Test that upward trend is detected."""
        now = datetime(2024, 1, 1, 12, 0, 0)
        mock_dt_util.utcnow.return_value = now
        
        # Record increasing temperatures
        for i in range(10):
            lwt_controller.record_temperature(20.0 + i * 0.05)
            mock_dt_util.utcnow.return_value = now + timedelta(minutes=i * 3)
        
        assert not lwt_controller._is_temp_trending_down()

    @patch('config.custom_components.heatpump_controller.climate.lwt_controller.dt_util')
    def test_trend_with_insufficient_data(self, mock_dt_util, lwt_controller):
        """Test that trend defaults to down with insufficient data."""
        now = datetime(2024, 1, 1, 12, 0, 0)
        mock_dt_util.utcnow.return_value = now
        
        # Only a few data points
        lwt_controller.record_temperature(21.0)
        
        # Should assume trending down
        assert lwt_controller._is_temp_trending_down()


class TestDeviationCalculation:
    """Test LWT deviation calculation."""

    def test_calculate_deviation_zero_demand(self, lwt_controller):
        """Test deviation calculation with zero heat demand."""
        deviation = lwt_controller.calculate_deviation(0.0)
        assert abs(deviation - 0.0) < 0.1  # Should be near middle of range

    def test_calculate_deviation_high_demand(self, lwt_controller):
        """Test deviation calculation with high heat demand."""
        deviation = lwt_controller.calculate_deviation(1.0)
        assert deviation > 5.0  # Should be toward max

    def test_calculate_deviation_negative_demand(self, lwt_controller):
        """Test deviation calculation with negative demand (too warm)."""
        deviation = lwt_controller.calculate_deviation(-1.0)
        assert deviation < -5.0  # Should be toward min

    @pytest.mark.asyncio
    async def test_set_lwt_deviation_clamping(self, lwt_controller, mock_hass):
        """Test that deviation is clamped to configured range."""
        # Try to set above max
        await lwt_controller.set_lwt_deviation(15.0)
        assert lwt_controller.current_deviation == 10.0
        
        # Try to set below min
        await lwt_controller.set_lwt_deviation(-15.0)
        assert lwt_controller.current_deviation == -10.0
        
        # Set within range
        await lwt_controller.set_lwt_deviation(5.0)
        assert lwt_controller.current_deviation == 5.0


class TestTemperatureHistoryManagement:
    """Test temperature history management."""

    @patch('config.custom_components.heatpump_controller.climate.lwt_controller.dt_util')
    def test_history_keeps_last_30_minutes(self, mock_dt_util, lwt_controller):
        """Test that temperature history only keeps last 30 minutes."""
        now = datetime(2024, 1, 1, 12, 0, 0)
        mock_dt_util.utcnow.return_value = now
        
        # Record temperatures over 60 minutes
        for i in range(120):  # 120 readings at 30 second intervals = 60 minutes
            lwt_controller.record_temperature(21.0)
            mock_dt_util.utcnow.return_value = now + timedelta(seconds=i * 30)
        
        # Should only have last 30 minutes (60 readings)
        assert len(lwt_controller._temp_history) <= 60
