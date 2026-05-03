"""Nutrislice School Menu – Home Assistant Custom Integration.

Fetches breakfast and lunch menus from any Nutrislice-powered school and:
  • Creates two sensor entities  (today's breakfast / lunch)
  • Creates one calendar entity  (calendar.nutrislice_<school>) that serves
    menu events directly to HA — no external calendar integration required
  • Registers a service  nutrislice_menu.sync_menu  that fetches fresh data
    on demand (call this from your own automation)
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import CONF_DISTRICT, CONF_SCHOOL, DOMAIN, SERVICE_SYNC_MENU
from .coordinator import NutrisliceCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR]

# HA 2024.4+ generic ConfigEntry — gives platform code typed access to the
# coordinator via entry.runtime_data, removing the hass.data bookkeeping.
NutrisliceConfigEntry = ConfigEntry[NutrisliceCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: NutrisliceConfigEntry) -> bool:
    """Set up Nutrislice School Menu from a config entry."""
    coordinator = NutrisliceCoordinator(
        hass, entry.data[CONF_DISTRICT], entry.data[CONF_SCHOOL]
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_sync_menu(call: ServiceCall) -> None:
        await coordinator.async_refresh()
        _LOGGER.info(
            "sync_menu complete – %d days loaded for %s/%s",
            len(coordinator.data or {}), coordinator.district, coordinator.school,
        )

    hass.services.async_register(DOMAIN, SERVICE_SYNC_MENU, handle_sync_menu)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NutrisliceConfigEntry) -> bool:
    """Unload the integration cleanly."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.services.async_remove(DOMAIN, SERVICE_SYNC_MENU)
    return unload_ok
