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

You can configure the controller to automatically adjust heating thresholds based on outdoor temperature. This allows for more aggressive heating in cold weather and more conservative operation in milder conditions.

To improve reliability, you can configure both a primary outdoor sensor and a fallback sensor. The fallback sensor will be used automatically if the primary sensor becomes unavailable:

```yaml
heatpump_controller:
  on_off_switch: switch.heatpump_power
  threshold_before_heat: 0.07
  threshold_before_off: 0.007
  threshold_room_needs_heat: 0.3
  outdoor_sensor: sensor.outdoor_temperature           # Primary sensor (e.g., cloud-based)
  outdoor_sensor_fallback: sensor.local_outdoor_temp   # Fallback sensor (e.g., local sensor)
  outdoor_thresholds:
    - min_temp: -10
      max_temp: 5
      threshold_before_heat: 0.03
      threshold_before_off: 0.003
    - min_temp: 5
      max_temp: 15
      threshold_before_heat: 0.07
      threshold_before_off: 0.007
    - min_temp: 15
      threshold_before_heat: 0.15
      threshold_before_off: 0.015
  rooms:
    - sensor: climate.living_room_thermostat
      weight: 1.5
    - sensor: climate.bedroom_thermostat
      weight: 1.0
```

**Outdoor Threshold Configuration:**
- `outdoor_sensor`: Entity ID of your primary outdoor temperature sensor
- `outdoor_sensor_fallback` (optional): Entity ID of a fallback outdoor temperature sensor. Used when the primary sensor is unavailable or returns invalid values.
- `outdoor_thresholds`: List of temperature ranges with their respective thresholds
  - `min_temp` (optional): Minimum temperature (inclusive) for this range
  - `max_temp` (optional): Maximum temperature (exclusive) for this range
  - `threshold_before_heat`: Override value for heating threshold
  - `threshold_before_off`: Override value for off threshold

**Important:** To enable outdoor temperature-based threshold adjustments, you must select the **"Weighted Average with Outdoor Temp"** algorithm from the algorithm selector entity. The outdoor threshold overrides will only be applied when this algorithm is active.

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

## Control Algorithms

The controller supports multiple control algorithms that can be selected via the `select.algorithm` entity:

### Manual
Disables automatic heatpump control. The controller will monitor temperatures and update sensors, but will not automatically turn the heatpump on or off.

### Weighted Average
Uses weighted average temperatures across all rooms to make heating decisions based on the configured base thresholds (`threshold_before_heat` and `threshold_before_off`).

### Weighted Average with Outdoor Temp
Extends the Weighted Average algorithm by dynamically adjusting heating thresholds based on outdoor temperature. When this algorithm is selected:
- The controller reads the outdoor temperature sensor
- Matches the temperature against configured `outdoor_thresholds` ranges
- Applies the corresponding threshold overrides for more intelligent heating control
- Logs INFO messages when threshold overrides are applied

**Note:** To use outdoor temperature-based threshold adjustments, you must:
1. Configure `outdoor_sensor` and `outdoor_thresholds` in your configuration
2. Select the "Weighted Average with Outdoor Temp" algorithm

### LWT Control
**For advanced heatpumps with weather-dependent curves and modulating capacity.**

This algorithm controls room temperature by adjusting the Leaving Water Temperature (LWT) deviation on the weather-dependent curve, rather than simple on/off control. This provides more precise temperature control and better energy efficiency.

**How it works:**
- Forces all room thermostat setpoints to maximum (e.g., 22°C) to keep TRV valves fully open
- Saves original setpoints and restores them when switching to a different algorithm
- Controls temperature by adjusting the LWT deviation within a configured range (default -10 to +10°C)
- Maps heat demand (`avg_needed_temp`) to appropriate LWT deviation
- Implements overcapacity detection to prevent overheating:
  - Detects when heatpump is at minimum capacity but still overproducing (LWT actual exceeds setpoint)
  - Turns off heatpump when overcapacity is sustained for configured duration (default 60 minutes)
  - Enforces minimum off time (default 30 minutes) to prevent compressor wear
  - Only restarts when room temperature is trending downward

**Configuration example:**
```yaml
heatpump_controller:
  on_off_switch: switch.heatpump_power
  threshold_before_heat: 0.07
  threshold_before_off: 0.007
  threshold_room_needs_heat: 0.3
  rooms:
    - sensor: climate.living_room_thermostat
      weight: 1.5
    - sensor: climate.bedroom_thermostat
      weight: 1.0
  
  # LWT Control configuration
  lwt_deviation_entity: number.heatpump_lwt_offset
  lwt_actual_sensor: sensor.heatpump_lwt_actual
  lwt_setpoint_sensor: sensor.heatpump_lwt_setpoint
  max_room_setpoint: 22.0                      # Max setpoint for TRV valves (optional, default: 22.0)
  lwt_deviation_min: -10                       # Minimum LWT deviation (optional, default: -10.0)
  lwt_deviation_max: 10                        # Maximum LWT deviation (optional, default: 10.0)
  min_off_time_minutes: 30                     # Minimum off time to prevent short-cycling (optional, default: 30)
  lwt_overcapacity_threshold: 1.0              # LWT difference threshold for overcapacity (optional, default: 1.0)
  lwt_overcapacity_duration_minutes: 60        # Duration before acting on overcapacity (optional, default: 60)
```

**Configuration parameters:**
- `lwt_deviation_entity` (required): Entity ID of the number entity that controls LWT deviation/offset
- `lwt_actual_sensor` (required): Entity ID of the sensor reporting actual LWT
- `lwt_setpoint_sensor` (required): Entity ID of the sensor reporting LWT setpoint from weather curve
- `max_room_setpoint` (optional): Maximum temperature setpoint for room thermostats (default: 22.0°C)
- `lwt_deviation_min` (optional): Minimum allowed LWT deviation (default: -10.0°C)
- `lwt_deviation_max` (optional): Maximum allowed LWT deviation (default: 10.0°C)
- `min_off_time_minutes` (optional): Minimum time heatpump must stay off to prevent short-cycling (default: 30 minutes)
- `lwt_overcapacity_threshold` (optional): Temperature difference threshold for detecting overcapacity (default: 1.0°C)
- `lwt_overcapacity_duration_minutes` (optional): Duration overcapacity must be sustained before turning off (default: 60 minutes)

**Additional sensors for LWT Control:**
- `sensor.heatpump_controller_lwt_deviation`: Current LWT deviation being applied
- `binary_sensor.lwt_overcapacity`: True when overcapacity condition is detected
- `sensor.lwt_off_time_remaining`: Minutes remaining in minimum off period (when applicable)

**Note:** Sensor entity IDs are auto-generated by Home Assistant based on the sensor names. To customize the entity IDs (e.g., to `sensor.hc_lwt_deviation_heating`), you can:
1. Rename them in Home Assistant's UI: Settings → Entities → Select the sensor → Change entity ID
2. Use `customize.yaml` to set custom entity IDs

**When to use:**
- You have a modulating heatpump with weather-dependent curves
- Your heatpump supports LWT offset/deviation control
- You want more precise temperature control than simple on/off
- You want to minimize short-cycling and maximize efficiency

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
      - sensor.outdoor_temperature
      - binary_sensor.paused
      - type: attribute
        entity: climate.heatpump_controller
        attribute: pause_until
        name: Paused until
  - type: markdown
    content: >
      ### Active Outdoor Mapping

      ```json

      {{ states('sensor.active_outdoor_mapping') | from_json | tojson(indent=2)
      }}

      ```
```

## Sensors

The controller exposes several sensors for monitoring:

**Note:** All sensor entity IDs listed below are auto-generated by Home Assistant. You can customize them through the Home Assistant UI (Settings → Entities) or using `customize.yaml` if you prefer different entity IDs.

### Temperature Sensors
- `sensor.heatpump_controller_average_temp`: Weighted average temperature across all rooms
- `sensor.heatpump_controller_avg_target_temp`: Weighted average target temperature
- `sensor.heatpump_controller_avg_needed_temp`: Average temperature gap to target
- `sensor.heatpump_controller_threshold_before_heat`: Active threshold before turning heat on
- `sensor.heatpump_controller_threshold_before_off`: Active threshold before turning heat off
- `sensor.heatpump_controller_threshold_room_needs_heat`: Per-room threshold for needing heat
- `sensor.heatpump_controller_outdoor_temp`: Current outdoor temperature (when configured)
- `sensor.heatpump_controller_lwt_deviation`: Current LWT deviation (when LWT Control is active)

### Other Sensors
- `sensor.rooms_below_target`: Number of rooms below their target temperature
- `sensor.heatpump_controller_active_outdoor_mapping`: Active outdoor temperature mapping as JSON (when applicable)
- `sensor.lwt_off_time_remaining`: Minutes remaining in minimum off period (when LWT Control is active)

### Binary Sensors
- `binary_sensor.any_room_below_threshold`: True if any room needs heat
- `binary_sensor.paused`: True if controller is paused
- `binary_sensor.lwt_overcapacity`: True when LWT overcapacity condition is detected (when LWT Control is active)