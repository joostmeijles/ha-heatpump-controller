# Heatpump controller

## Markdown card
Add the Heatpump controller as Markdown card:

```
- **Mode:** {{ states('climate.heat_pump_controller') }}
- **Avg temp:** {{ state_attr('climate.heat_pump_controller', 'current_temperature') | round(3) }} °C
- **Avg target temp:** {{ state_attr('climate.heat_pump_controller', 'temperature') | round(3) }} °C
- **Avg needed temp:** {{ state_attr('climate.heat_pump_controller', 'avg_needed_temp') | round(3) }} °C
- **Number of rooms below target:** {{ state_attr('climate.heat_pump_controller', 'num_rooms_below_target') }}
- **Threshold before HEAT:** {{ state_attr('climate.heat_pump_controller', 'threshold_before_heat') }} °C
- **Threshold before OFF:** {{ state_attr('climate.heat_pump_controller', 'threshold_before_off') }} °C
```