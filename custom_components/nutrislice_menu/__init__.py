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

from .const import (
    CONF_DISTRICT,
    CONF_SCHOOL,
    DATA_COORDINATOR,
    DOMAIN,
    SERVICE_SYNC_MENU,
)
from .coordinator import NutrisliceCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Nutrislice School Menu from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    district: str = entry.data[CONF_DISTRICT]
    school:   str = entry.data[CONF_SCHOOL]

    coordinator = NutrisliceCoordinator(hass, district, school)

    # First fetch — UpdateFailed is automatically converted to ConfigEntryNotReady
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # ── Register sync_menu service ────────────────────────────────────────────
    async def handle_sync_menu(call: ServiceCall) -> None:
        """Refresh Nutrislice data on demand.

        The coordinator notifies all entities (sensors + calendar) of the
        new data automatically via the CoordinatorEntity listener mechanism.
        No manual calendar writes needed.
        """
        _LOGGER.info("sync_menu: refreshing data for %s/%s", district, school)
        await coordinator.async_refresh()
        _LOGGER.info(
            "sync_menu complete – %d days loaded for %s/%s",
            len(coordinator.data or {}), district, school,
        )

    hass.services.async_register(DOMAIN, SERVICE_SYNC_MENU, handle_sync_menu)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the integration cleanly."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        hass.services.async_remove(DOMAIN, SERVICE_SYNC_MENU)

    return unload_ok
