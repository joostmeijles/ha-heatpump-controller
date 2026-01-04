# Heatpump controller

## Markdown card
Add the Heatpump controller as Markdown card:

```
type: vertical-stack
cards:
  - type: markdown
    title: Heatpump Controller
    content: |
      - **Heatpump mode:** {{ states('climate.heat_pump_controller') }}
      - **Algorithm:** {{ states('select.heatpump_control_algorithm') }}
      - **Avg temp:** {{ state_attr('climate.heat_pump_controller', 'current_temp_high_precision') }} °C
      - **Avg target temp:** {{ state_attr('climate.heat_pump_controller', 'target_temp_high_precision') }} °C
      - **Avg needed temp:** {{ state_attr('climate.heat_pump_controller', 'avg_needed_temp') }} °C
      - **Any room below threshold:** {{ state_attr('climate.heat_pump_controller', 'any_room_needs_heat') }}
      - **Number of rooms below target:** {{ state_attr('climate.heat_pump_controller', 'num_rooms_below_target') }}
      - **Threshold before HEAT:** {{ state_attr('climate.heat_pump_controller', 'threshold_before_heat') }} °C
      - **Threshold before OFF:** {{ state_attr('climate.heat_pump_controller', 'threshold_before_off') }} °C
      - **Threshold room needs HEAT:** {{ state_attr('climate.heat_pump_controller', 'threshold_room_needs_heat') }} °C
      - **Paused:** {{ state_attr('climate.heat_pump_controller', 'paused') }}
      - **Paused until:** {{ state_attr('climate.heat_pump_controller', 'pause_until') }}

  - type: entities
    entities:
      - select.heatpump_control_algorithm
```