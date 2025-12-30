from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    ClimateEntityFeature,
)
from homeassistant.const import UnitOfTemperature

class HeatPumpThermostat(ClimateEntity):
    _attr_name = "Heat Pump"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]

    def __init__(self):
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = 21.0
        self._attr_current_temperature = 20.0

    async def async_set_temperature(self, **kwargs):
        if "temperature" in kwargs:
            self._attr_target_temperature = kwargs["temperature"]
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    async_add_entities([HeatPumpThermostat()])
