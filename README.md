# Heatpump controller

## Card
Add the Heatpump controller as card:

```
type: vertical-stack
cards:
  - type: entities
    entities:
      - climate.heatpump_controller
      - select.heatpump_control_algorithm
      - binary_sensor.any_room_below_threshold
      - sensor.rooms_below_target
      - sensor.heatpump_controller_average_temp
      - sensor.heatpump_controller_avg_target_temp
      - sensor.heatpump_controller_avg_needed_temp
      - sensor.heatpump_controller_threshold_before_heat
      - sensor.heatpump_controller_threshold_before_off
      - sensor.heatpump_controller_threshold_room_needs_heat
      - binary_sensor.paused
      - type: attribute
        entity: climate.heatpump_controller
        attribute: pause_until
        name: Paused until
```