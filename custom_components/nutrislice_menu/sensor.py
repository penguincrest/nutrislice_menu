"""Sensor platform for Nutrislice School Menu.

Creates two sensors:
  sensor.<school>_breakfast_today
  sensor.<school>_lunch_today

Display date logic:
  Before 9:30 AM  → show TODAY's menu
  9:30 AM onwards → show TOMORROW's menu

This means the card always shows the next upcoming school meal.
The sensors re-evaluate at 9:30 AM every day via a time-change listener,
and whenever the coordinator data refreshes.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

import homeassistant.util.dt as dt_util
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN, MENU_TYPES
from .coordinator import NutrisliceCoordinator

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

# Time of day at which we flip to showing tomorrow's menu
FLIP_HOUR   = 9
FLIP_MINUTE = 30


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from the config entry."""
    coordinator: NutrisliceCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    async_add_entities(
        [NutrisliceMenuSensor(coordinator, meal_type, entry.entry_id)
         for meal_type in MENU_TYPES],
        update_before_add=False,
    )


class NutrisliceMenuSensor(CoordinatorEntity[NutrisliceCoordinator], SensorEntity):
    """Sensor that surfaces the upcoming menu for one meal type.

    Shows today's menu before FLIP_HOUR:FLIP_MINUTE, then flips to
    tomorrow's menu for the rest of the day.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:silverware-fork-knife"

    def __init__(
        self,
        coordinator: NutrisliceCoordinator,
        meal_type: str,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._meal_type = meal_type
        self._attr_unique_id = (
            f"{DOMAIN}_{coordinator.district}_{coordinator.school}_{meal_type}_today"
        )
        self._attr_name = f"{meal_type.capitalize()} Today"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=f"{coordinator.school.replace('-', ' ').title()} Menu",
            manufacturer="Nutrislice",
            model="School Menu",
            entry_type=DeviceEntryType.SERVICE,
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def async_added_to_hass(self) -> None:
        """Register a 9:30 AM time listener to flip the display date."""
        await super().async_added_to_hass()

        @callback
        def _handle_flip(_now: datetime.datetime) -> None:
            """Called at 9:30 AM every day — push a state update."""
            _LOGGER.debug(
                "%s flipping display date at %s", self.entity_id, _now.isoformat()
            )
            self.async_write_ha_state()

        # Register the daily flip; cancel it on unload automatically
        self.async_on_remove(
            async_track_time_change(
                self.hass,
                _handle_flip,
                hour=FLIP_HOUR,
                minute=FLIP_MINUTE,
                second=0,
            )
        )

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def native_value(self) -> str | None:
        items = self._display_items()
        return ", ".join(i["name"] for i in items) if items else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        items = self._display_items()
        display_date = self._display_date()
        return {
            "items":        items,
            "hero_image":   next((i["image"] for i in items if i.get("image")), ""),
            "meal_type":    self._meal_type,
            "date":         display_date.isoformat(),
            "showing":      "tomorrow" if self._is_showing_tomorrow() else "today",
            "school":       self.coordinator.school,
            "district":     self.coordinator.district,
        }

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _is_showing_tomorrow(self) -> bool:
        """Return True if the current local time is at or after the flip time."""
        now = dt_util.now()
        flip = now.replace(
            hour=FLIP_HOUR, minute=FLIP_MINUTE, second=0, microsecond=0
        )
        return now >= flip

    def _display_date(self) -> datetime.date:
        """Return the next school day whose menu should be shown right now.

        After 9:30 AM we advance one day, then skip Saturday and Sunday so
        the card never tries to show a weekend menu.

        Examples:
          Friday    08:00  -> Friday
          Friday    09:30  -> Monday  (skips Sat + Sun)
          Saturday  any    -> Monday  (always skips to next weekday)
          Sunday    any    -> Monday  (always skips to next weekday)
        """
        base = dt_util.now().date()
        if self._is_showing_tomorrow():
            base += datetime.timedelta(days=1)
        # Saturday=5, Sunday=6 — keep advancing until we land on a weekday
        while base.weekday() >= 5:
            base += datetime.timedelta(days=1)
        return base

    def _display_items(self) -> list[dict[str, str]]:
        """Return menu items for the display date."""
        if not self.coordinator.data:
            return []
        date_str = self._display_date().isoformat()
        return self.coordinator.data.get(date_str, {}).get(self._meal_type, [])
