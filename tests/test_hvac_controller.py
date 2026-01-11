"""Tests for hvac_controller module."""


from datetime import timedelta
from unittest.mock import patch
from homeassistant.components.climate.const import HVACMode
from config.custom_components.heatpump_controller.climate.hvac_controller import HVACController


class TestHVACControllerInitialization:
    """Test HVACController initialization."""

    def test_initialization(self):
        """Test controller initialization with basic parameters."""
        controller = HVACController(0.07, 0.007, 0.3)
        
        assert controller.threshold_before_heat == 0.07
        assert controller.threshold_before_off == 0.007
        assert controller.threshold_room_needs_heat == 0.3
        assert not controller.is_paused


class TestHVACControllerProperties:
    """Test HVACController properties."""

    def test_threshold_getters_and_setters(self):
        """Test threshold getter and setter properties."""
        controller = HVACController(0.07, 0.007, 0.3)
        
        # Test initial values
        assert controller.threshold_before_heat == 0.07
        assert controller.threshold_before_off == 0.007
        
        # Test setters
        controller.threshold_before_heat = 0.1
        controller.threshold_before_off = 0.01
        
        assert controller.threshold_before_heat == 0.1
        assert controller.threshold_before_off == 0.01


class TestPauseLogic:
    """Test pause functionality."""

    @patch('config.custom_components.heatpump_controller.climate.hvac_controller.dt_util')
    def test_set_pause(self, mock_dt_util):
        """Test setting pause."""
        from datetime import datetime
        now = datetime(2024, 1, 1, 12, 0, 0)
        mock_dt_util.utcnow.return_value = now
        
        controller = HVACController(0.07, 0.007, 0.3)
        controller.set_pause(30)
        
        expected_pause_until = now + timedelta(minutes=30)
        assert controller.get_pause_until() == expected_pause_until

    @patch('config.custom_components.heatpump_controller.climate.hvac_controller.dt_util')
    def test_is_paused_active(self, mock_dt_util):
        """Test is_paused when pause is active."""
        from datetime import datetime
        now = datetime(2024, 1, 1, 12, 0, 0)
        mock_dt_util.utcnow.return_value = now
        
        controller = HVACController(0.07, 0.007, 0.3)
        controller.set_pause(30)
        
        # Still within pause period
        mock_dt_util.utcnow.return_value = now + timedelta(minutes=15)
        assert controller.is_paused is True

    @patch('config.custom_components.heatpump_controller.climate.hvac_controller.dt_util')
    def test_is_paused_expired(self, mock_dt_util):
        """Test is_paused when pause has expired."""
        from datetime import datetime
        now = datetime(2024, 1, 1, 12, 0, 0)
        mock_dt_util.utcnow.return_value = now
        
        controller = HVACController(0.07, 0.007, 0.3)
        controller.set_pause(30)
        
        # After pause period
        mock_dt_util.utcnow.return_value = now + timedelta(minutes=31)
        assert controller.is_paused is False

    def test_is_paused_not_set(self):
        """Test is_paused when pause was never set."""
        controller = HVACController(0.07, 0.007, 0.3)
        assert controller.is_paused is False


class TestUpdateHVACMode:
    """Test HVAC mode update logic."""

    @patch('config.custom_components.heatpump_controller.climate.hvac_controller.dt_util')
    def test_paused_turns_off(self, mock_dt_util):
        """Test that paused state turns heat off."""
        from datetime import datetime
        now = datetime(2024, 1, 1, 12, 0, 0)
        mock_dt_util.utcnow.return_value = now
        
        controller = HVACController(0.07, 0.007, 0.3)
        controller.set_pause(30)
        
        # Check paused state turns heat off
        mock_dt_util.utcnow.return_value = now + timedelta(minutes=15)
        mode = controller.update_hvac_mode(HVACMode.HEAT, 0.1, False)
        assert mode == HVACMode.OFF

    @patch('config.custom_components.heatpump_controller.climate.hvac_controller.dt_util')
    def test_paused_keeps_off(self, mock_dt_util):
        """Test that paused state keeps heat off."""
        from datetime import datetime
        now = datetime(2024, 1, 1, 12, 0, 0)
        mock_dt_util.utcnow.return_value = now
        
        controller = HVACController(0.07, 0.007, 0.3)
        controller.set_pause(30)
        
        # Check paused state keeps heat off
        mock_dt_util.utcnow.return_value = now + timedelta(minutes=15)
        mode = controller.update_hvac_mode(HVACMode.OFF, 0.1, False)
        assert mode == HVACMode.OFF

    def test_any_room_needs_heat_override(self):
        """Test that any_room_needs_heat turns heat on."""
        controller = HVACController(0.07, 0.007, 0.3)
        
        mode = controller.update_hvac_mode(HVACMode.OFF, 0.05, True)
        assert mode == HVACMode.HEAT

    def test_any_room_needs_heat_keeps_on(self):
        """Test that any_room_needs_heat keeps heat on."""
        controller = HVACController(0.07, 0.007, 0.3)
        
        mode = controller.update_hvac_mode(HVACMode.HEAT, 0.05, True)
        assert mode == HVACMode.HEAT

    def test_turn_heat_on_threshold_reached(self):
        """Test turning heat on when threshold is reached."""
        controller = HVACController(0.07, 0.007, 0.3)
        
        # Off mode, avg_needed_temp >= threshold_before_heat
        mode = controller.update_hvac_mode(HVACMode.OFF, 0.08, False)
        assert mode == HVACMode.HEAT

    def test_turn_heat_on_threshold_exact(self):
        """Test turning heat on when exactly at threshold."""
        controller = HVACController(0.07, 0.007, 0.3)
        
        # Off mode, avg_needed_temp == threshold_before_heat
        mode = controller.update_hvac_mode(HVACMode.OFF, 0.07, False)
        assert mode == HVACMode.HEAT

    def test_stay_off_below_threshold(self):
        """Test staying off when below threshold."""
        controller = HVACController(0.07, 0.007, 0.3)
        
        # Off mode, avg_needed_temp < threshold_before_heat
        mode = controller.update_hvac_mode(HVACMode.OFF, 0.05, False)
        assert mode == HVACMode.OFF

    def test_turn_heat_off_below_threshold(self):
        """Test turning heat off when below off threshold."""
        controller = HVACController(0.07, 0.007, 0.3)
        
        # Heat mode, avg_needed_temp < threshold_before_off
        mode = controller.update_hvac_mode(HVACMode.HEAT, 0.005, False)
        assert mode == HVACMode.OFF

    def test_stay_on_above_off_threshold(self):
        """Test staying on when above off threshold."""
        controller = HVACController(0.07, 0.007, 0.3)
        
        # Heat mode, avg_needed_temp >= threshold_before_off
        mode = controller.update_hvac_mode(HVACMode.HEAT, 0.01, False)
        assert mode == HVACMode.HEAT

    def test_hysteresis_in_middle(self):
        """Test hysteresis: stay in current mode when in middle zone."""
        controller = HVACController(0.07, 0.007, 0.3)
        
        # Between thresholds: 0.007 <= 0.05 < 0.07
        # Should stay in current mode
        mode_was_off = controller.update_hvac_mode(HVACMode.OFF, 0.05, False)
        assert mode_was_off == HVACMode.OFF
        
        mode_was_heat = controller.update_hvac_mode(HVACMode.HEAT, 0.05, False)
        assert mode_was_heat == HVACMode.HEAT


class TestEdgeCases:
    """Test edge cases in HVAC controller."""

    def test_zero_thresholds(self):
        """Test with zero thresholds."""
        controller = HVACController(0.0, 0.0, 0.0)
        
        # Any positive needed temp should turn heat on
        mode = controller.update_hvac_mode(HVACMode.OFF, 0.001, False)
        assert mode == HVACMode.HEAT
        
        # Any negative or zero needed temp should turn heat off
        mode = controller.update_hvac_mode(HVACMode.HEAT, -0.001, False)
        assert mode == HVACMode.OFF

    def test_negative_needed_temp(self):
        """Test with negative needed temperature (rooms above target)."""
        controller = HVACController(0.07, 0.007, 0.3)
        
        # Heat should turn off
        mode = controller.update_hvac_mode(HVACMode.HEAT, -1.0, False)
        assert mode == HVACMode.OFF

    def test_very_high_needed_temp(self):
        """Test with very high needed temperature."""
        controller = HVACController(0.07, 0.007, 0.3)
        
        # Heat should turn on
        mode = controller.update_hvac_mode(HVACMode.OFF, 10.0, False)
        assert mode == HVACMode.HEAT

    def test_threshold_update_during_operation(self):
        """Test updating thresholds during operation."""
        controller = HVACController(0.07, 0.007, 0.3)
        
        # Initially, 0.05 is below heat threshold
        mode = controller.update_hvac_mode(HVACMode.OFF, 0.05, False)
        assert mode == HVACMode.OFF
        
        # Update threshold to be lower
        controller.threshold_before_heat = 0.04
        
        # Now 0.05 should turn heat on
        mode = controller.update_hvac_mode(HVACMode.OFF, 0.05, False)
        assert mode == HVACMode.HEAT


class TestPriorityOrder:
    """Test priority order of different conditions."""

    @patch('config.custom_components.heatpump_controller.climate.hvac_controller.dt_util')
    def test_pause_overrides_any_room_needs_heat(self, mock_dt_util):
        """Test that pause takes priority over any_room_needs_heat."""
        from datetime import datetime
        now = datetime(2024, 1, 1, 12, 0, 0)
        mock_dt_util.utcnow.return_value = now
        
        controller = HVACController(0.07, 0.007, 0.3)
        controller.set_pause(30)
        
        # Even with any_room_needs_heat=True, should be OFF
        mock_dt_util.utcnow.return_value = now + timedelta(minutes=15)
        mode = controller.update_hvac_mode(HVACMode.HEAT, 0.1, True)
        assert mode == HVACMode.OFF

    def test_any_room_needs_heat_overrides_hysteresis(self):
        """Test that any_room_needs_heat overrides hysteresis."""
        controller = HVACController(0.07, 0.007, 0.3)
        
        # avg_needed_temp is below threshold but any_room_needs_heat=True
        mode = controller.update_hvac_mode(HVACMode.OFF, 0.01, True)
        assert mode == HVACMode.HEAT
