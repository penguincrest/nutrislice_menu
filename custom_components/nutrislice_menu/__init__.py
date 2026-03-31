"""Nutrislice School Menu – Home Assistant Custom Integration.

Fetches breakfast and lunch menus from any Nutrislice-powered school and:
  • Creates two sensor entities (today's breakfast / lunch)
  • Registers a service  nutrislice_menu.sync_menu  that fetches fresh data
    and writes events to the configured calendar entity

Scheduling is entirely up to the user – call sync_menu from an automation.
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .calendar_writer import write_calendar_events
from .const import (
    CONF_CALENDAR_ENTITY,
    CONF_DISTRICT,
    CONF_SCHOOL,
    DATA_CALENDAR_ENTITY,
    DATA_COORDINATOR,
    DEFAULT_CALENDAR_ENTITY,
    DOMAIN,
    SERVICE_SYNC_MENU,
)
from .coordinator import NutrisliceCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Nutrislice School Menu from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    district: str = entry.data[CONF_DISTRICT]
    school:   str = entry.data[CONF_SCHOOL]
    calendar_entity_id: str = entry.data.get(
        CONF_CALENDAR_ENTITY, DEFAULT_CALENDAR_ENTITY
    )

    coordinator = NutrisliceCoordinator(hass, district, school)

    # First refresh – UpdateFailed is automatically converted to ConfigEntryNotReady
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR:     coordinator,
        DATA_CALENDAR_ENTITY: calendar_entity_id,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # ── Register sync_menu service ────────────────────────────────────────────
    async def handle_sync_menu(call: ServiceCall) -> None:
        """Fetch fresh Nutrislice data, update sensors, write calendar events."""
        _LOGGER.info(
            "sync_menu: fetching %s/%s → %s", district, school, calendar_entity_id
        )
        await coordinator.async_refresh()

        if not coordinator.data:
            _LOGGER.warning("sync_menu: no data returned from Nutrislice")
            return

        await write_calendar_events(
            hass, calendar_entity_id, coordinator.data, district, school
        )
        _LOGGER.info(
            "sync_menu complete – %d days written to %s",
            len(coordinator.data), calendar_entity_id,
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
