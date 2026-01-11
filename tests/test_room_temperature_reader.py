"""Tests for room_temperature_reader module."""


from unittest.mock import Mock
from config.custom_components.heatpump_controller.room_temperature_reader import (
    read_sensor_temperature,
    read_room_temperatures,
)


class TestReadSensorTemperature:
    """Test the read_sensor_temperature function."""

    def test_successful_read(self, mock_hass, mock_state):
        """Test successful temperature reading."""
        state = mock_state("sensor.outdoor", "15.5", {})
        mock_hass.states.get.return_value = state
        
        temp = read_sensor_temperature(mock_hass, "sensor.outdoor", "Outdoor")
        
        assert temp == 15.5
        mock_hass.states.get.assert_called_once_with("sensor.outdoor")

    def test_sensor_not_configured(self, mock_hass):
        """Test when sensor is None."""
        temp = read_sensor_temperature(mock_hass, None, "Outdoor")
        
        assert temp is None
        mock_hass.states.get.assert_not_called()

    def test_sensor_not_found(self, mock_hass):
        """Test when sensor entity is not found."""
        mock_hass.states.get.return_value = None
        
        temp = read_sensor_temperature(mock_hass, "sensor.missing", "Outdoor")
        
        assert temp is None

    def test_non_numeric_state(self, mock_hass, mock_state):
        """Test when sensor has non-numeric state."""
        state = mock_state("sensor.outdoor", "unavailable", {})
        mock_hass.states.get.return_value = state
        
        temp = read_sensor_temperature(mock_hass, "sensor.outdoor", "Outdoor")
        
        assert temp is None

    def test_numeric_string_state(self, mock_hass, mock_state):
        """Test when sensor state is numeric string."""
        state = mock_state("sensor.outdoor", "20.5", {})
        mock_hass.states.get.return_value = state
        
        temp = read_sensor_temperature(mock_hass, "sensor.outdoor", "Outdoor")
        
        assert temp == 20.5

    def test_negative_temperature(self, mock_hass, mock_state):
        """Test reading negative temperature."""
        state = mock_state("sensor.outdoor", "-5.5", {})
        mock_hass.states.get.return_value = state
        
        temp = read_sensor_temperature(mock_hass, "sensor.outdoor", "Outdoor")
        
        assert temp == -5.5

    def test_zero_temperature(self, mock_hass, mock_state):
        """Test reading zero temperature."""
        state = mock_state("sensor.outdoor", "0.0", {})
        mock_hass.states.get.return_value = state
        
        temp = read_sensor_temperature(mock_hass, "sensor.outdoor", "Outdoor")
        
        assert temp == 0.0

    def test_integer_state(self, mock_hass, mock_state):
        """Test when sensor state is integer."""
        state = mock_state("sensor.outdoor", "20", {})
        mock_hass.states.get.return_value = state
        
        temp = read_sensor_temperature(mock_hass, "sensor.outdoor", "Outdoor")
        
        assert temp == 20.0


class TestReadRoomTemperatures:
    """Test the read_room_temperatures function."""

    def test_read_all_rooms_successfully(self, mock_hass, mock_state, sample_room_configs):
        """Test reading temperatures from all rooms successfully."""
        # Setup mock states
        states = {
            "climate.living_room": mock_state(
                "climate.living_room",
                "20.0",
                {"temperature_target": 22.0, "friendly_name": "Living Room"}
            ),
            "climate.bedroom": mock_state(
                "climate.bedroom",
                "19.0",
                {"temperature_target": 21.0, "friendly_name": "Bedroom"}
            ),
            "climate.office": mock_state(
                "climate.office",
                "21.0",
                {"temperature_target": 22.0, "friendly_name": "Office"}
            ),
        }
        mock_hass.states.get.side_effect = lambda entity_id: states.get(entity_id)
        
        temps = read_room_temperatures(mock_hass, sample_room_configs)
        
        assert len(temps) == 3
        assert temps[0] == (20.0, 22.0, 1.0)
        assert temps[1] == (19.0, 21.0, 1.5)
        assert temps[2] == (21.0, 22.0, 1.0)

    def test_missing_sensor(self, mock_hass, sample_room_configs):
        """Test when one sensor is missing."""
        # Only return state for first two rooms
        def get_state(entity_id):
            if entity_id == "climate.living_room":
                state = Mock()
                state.state = "20.0"
                state.attributes = {"temperature_target": 22.0, "friendly_name": "Living Room"}
                return state
            elif entity_id == "climate.bedroom":
                state = Mock()
                state.state = "19.0"
                state.attributes = {"temperature_target": 21.0, "friendly_name": "Bedroom"}
                return state
            return None
        
        mock_hass.states.get.side_effect = get_state
        
        temps = read_room_temperatures(mock_hass, sample_room_configs)
        
        assert len(temps) == 2
        assert temps[0] == (20.0, 22.0, 1.0)
        assert temps[1] == (19.0, 21.0, 1.5)

    def test_invalid_temperature(self, mock_hass, sample_room_configs):
        """Test when one sensor has invalid temperature."""
        def get_state(entity_id):
            if entity_id == "climate.living_room":
                state = Mock()
                state.state = "20.0"
                state.attributes = {"temperature_target": 22.0, "friendly_name": "Living Room"}
                return state
            elif entity_id == "climate.bedroom":
                state = Mock()
                state.state = "unavailable"
                state.attributes = {"temperature_target": 21.0, "friendly_name": "Bedroom"}
                return state
            elif entity_id == "climate.office":
                state = Mock()
                state.state = "21.0"
                state.attributes = {"temperature_target": 22.0, "friendly_name": "Office"}
                return state
            return None
        
        mock_hass.states.get.side_effect = get_state
        
        temps = read_room_temperatures(mock_hass, sample_room_configs)
        
        assert len(temps) == 2
        assert temps[0] == (20.0, 22.0, 1.0)
        assert temps[1] == (21.0, 22.0, 1.0)

    def test_missing_target_temperature(self, mock_hass):
        """Test when temperature_target attribute is missing."""
        rooms = [{"sensor": "climate.living_room", "weight": 1.0}]
        
        state = Mock()
        state.state = "20.0"
        # Use a Mock object for attributes to allow get() method override
        state.attributes = Mock()
        state.attributes.get = Mock(return_value=0.0)
        mock_hass.states.get.return_value = state
        
        temps = read_room_temperatures(mock_hass, rooms)
        
        assert len(temps) == 1
        assert temps[0] == (20.0, 0.0, 1.0)

    def test_empty_room_list(self, mock_hass):
        """Test with empty room list."""
        temps = read_room_temperatures(mock_hass, [])
        
        assert temps == []
        mock_hass.states.get.assert_not_called()

    def test_friendly_name_fallback(self, mock_hass):
        """Test that sensor entity_id is used when friendly_name is missing."""
        rooms = [{"sensor": "climate.living_room", "weight": 1.0}]
        
        state = Mock()
        state.state = "20.0"
        # Use a simple dict for attributes, the code will handle missing friendly_name
        state.attributes = {"temperature_target": 22.0}
        mock_hass.states.get.return_value = state
        
        temps = read_room_temperatures(mock_hass, rooms)
        
        assert len(temps) == 1
        assert temps[0] == (20.0, 22.0, 1.0)

