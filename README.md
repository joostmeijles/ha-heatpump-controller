# Heatpump controller

## Configuration

### Basic Configuration
Configure the heatpump controller in your `configuration.yaml`:

```yaml
heatpump_controller:
  - on_off_switch: switch.heatpump_power
  - threshold_before_heat: 0.07
  - threshold_before_off: 0.007
  - threshold_room_needs_heat: 0.3
  - rooms:
      - sensor: climate.living_room_thermostat
        weight: 1.5
      - sensor: climate.bedroom_thermostat
        weight: 1.0
```

### Outdoor Temperature-Based Threshold Adjustments (Optional)

You can configure the controller to automatically adjust heating thresholds based on outdoor temperature. This allows for more aggressive heating in cold weather and more conservative operation in milder conditions:

```yaml
heatpump_controller:
  - on_off_switch: switch.heatpump_power
  - threshold_before_heat: 0.07
  - threshold_before_off: 0.007
  - threshold_room_needs_heat: 0.3
  - outdoor_sensor: sensor.outdoor_temperature
  - outdoor_thresholds:
      - min_temp: -10
        max_temp: 5
        threshold_before_heat: 0.15
        threshold_before_off: 0.015
      - min_temp: 5
        max_temp: 15
        threshold_before_heat: 0.07
        threshold_before_off: 0.007
      - min_temp: 15
        threshold_before_heat: 0.03
        threshold_before_off: 0.003
  - rooms:
      - sensor: climate.living_room_thermostat
        weight: 1.5
      - sensor: climate.bedroom_thermostat
        weight: 1.0
```

**Outdoor Threshold Configuration:**
- `outdoor_sensor`: Entity ID of your outdoor temperature sensor
- `outdoor_thresholds`: List of temperature ranges with their respective thresholds
  - `min_temp` (optional): Minimum temperature (inclusive) for this range
  - `max_temp` (optional): Maximum temperature (exclusive) for this range
  - `threshold_before_heat`: Override value for heating threshold
  - `threshold_before_off`: Override value for off threshold

**Matching Rules:**
- Mappings are evaluated in the order they are defined
- First matching range is applied
- `min_temp <= outdoor_temp < max_temp` when both are specified
- `outdoor_temp >= min_temp` when only min_temp is specified
- `outdoor_temp < max_temp` when only max_temp is specified
- If neither min_temp nor max_temp is specified, acts as a fallback

**Backwards Compatibility:**
- If `outdoor_sensor` or `outdoor_thresholds` are not configured, base thresholds are used
- If outdoor sensor is unavailable or returns non-numeric values, base thresholds are used
- New sensors will show as unavailable/None when outdoor features are not configured or active

## Card
Add the Heatpump controller as card:

```
type: vertical-stack
cards:
  - type: entities
    entities:
      - climate.heatpump_controller
      - select.algorithm
      - binary_sensor.any_room_below_threshold
      - sensor.rooms_below_target
      - sensor.heatpump_controller_average_temp
      - sensor.heatpump_controller_avg_target_temp
      - sensor.heatpump_controller_avg_needed_temp
      - sensor.heatpump_controller_threshold_before_heat
      - sensor.heatpump_controller_threshold_before_off
      - sensor.heatpump_controller_threshold_room_needs_heat
      - sensor.heatpump_controller_outdoor_temp
      - sensor.heatpump_controller_active_outdoor_mapping
      - binary_sensor.paused
      - type: attribute
        entity: climate.heatpump_controller
        attribute: pause_until
        name: Paused until
```

## Sensors

The controller exposes several sensors for monitoring:

### Temperature Sensors
- `sensor.heatpump_controller_average_temp`: Weighted average temperature across all rooms
- `sensor.heatpump_controller_avg_target_temp`: Weighted average target temperature
- `sensor.heatpump_controller_avg_needed_temp`: Average temperature gap to target
- `sensor.heatpump_controller_threshold_before_heat`: Active threshold before turning heat on
- `sensor.heatpump_controller_threshold_before_off`: Active threshold before turning heat off
- `sensor.heatpump_controller_threshold_room_needs_heat`: Per-room threshold for needing heat
- `sensor.heatpump_controller_outdoor_temp`: Current outdoor temperature (when configured)

### Other Sensors
- `sensor.rooms_below_target`: Number of rooms below their target temperature
- `sensor.heatpump_controller_active_outdoor_mapping`: Active outdoor temperature mapping as JSON (when applicable)

### Binary Sensors
- `binary_sensor.any_room_below_threshold`: True if any room needs heat
- `binary_sensor.paused`: True if controller is paused