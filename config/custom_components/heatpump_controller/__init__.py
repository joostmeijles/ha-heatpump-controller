from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.discovery import async_load_platform

from .const import CONTROLLER, DOMAIN
from .climate import create_from_config


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    controller = create_from_config(hass, config[DOMAIN])
    hass.data.setdefault(DOMAIN, {})[CONTROLLER] = controller

    # Forward setup to platforms
    hass.async_create_task(
        async_load_platform(
            hass,
            Platform.CLIMATE,
            DOMAIN,
            {CONTROLLER: controller},
            config
        )
    )

    hass.async_create_task(
        async_load_platform(
            hass,
            Platform.SELECT,
            DOMAIN,
            {CONTROLLER: controller},
            config
        )
    )

    hass.async_create_task(
        async_load_platform(
            hass,
            Platform.SENSOR,
            DOMAIN,
            {CONTROLLER: controller},
            config
        )
    )

    hass.async_create_task(
        async_load_platform(
            hass,
            Platform.BINARY_SENSOR,
            DOMAIN,
            {CONTROLLER: controller},
            config
        )
    )

    return True
