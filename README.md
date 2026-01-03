# Heatpump controller

## Markdown card
Add the Heatpump controller as Markdown card:

```
- **Mode:** {{ states('climate.heat_pump_controller') }}
- **Avg temp:** {{ state_attr('climate.heat_pump_controller', 'current_temp_high_precision') }} °C
- **Avg target temp:** {{ state_attr('climate.heat_pump_controller', 'target_temp_high_precision') }} °C
- **Avg needed temp:** {{ state_attr('climate.heat_pump_controller', 'avg_needed_temp') }} °C
- **Any room below threshold:** {{ state_attr('climate.heat_pump_controller', 'any_room_needs_heat') }}
- **Number of rooms below target:** {{ state_attr('climate.heat_pump_controller', 'num_rooms_below_target') }}
- **Threshold before HEAT:** {{ state_attr('climate.heat_pump_controller', 'threshold_before_heat') }} °C
- **Threshold before OFF:** {{ state_attr('climate.heat_pump_controller', 'threshold_before_off') }} °C
- **Threshold room needs HEAT:** {{ state_attr('climate.heat_pump_controller', 'threshold_room_needs_heat') }} °C
```