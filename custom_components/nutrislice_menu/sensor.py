"""Sensor platform for Nutrislice School Menu.

Creates two sensors (sensor.<school>_breakfast_today and ..._lunch_today).

Display date logic:
  Before 9:30 AM  → show TODAY's menu
  9:30 AM onwards → show TOMORROW's menu
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

import homeassistant.util.dt as dt_util
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NutrisliceConfigEntry
from .const import DOMAIN, MENU_TYPES
from .coordinator import NutrisliceCoordinator

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

# Time of day at which we flip to showing tomorrow's menu
FLIP_HOUR = 9
FLIP_MINUTE = 30


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NutrisliceConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from the config entry."""
    async_add_entities(
        NutrisliceMenuSensor(entry.runtime_data, mt, entry.entry_id)
        for mt in MENU_TYPES
    )


class NutrisliceMenuSensor(CoordinatorEntity[NutrisliceCoordinator], SensorEntity):
    """Surfaces the upcoming menu for one meal type."""

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

    @property
    def available(self) -> bool:
        # Stay available across transient sync failures so the card keeps showing
        # the last known menu instead of "Sensor unavailable".
        return self.coordinator.data is not None

    async def async_added_to_hass(self) -> None:
        """Push a state update at the daily flip time."""
        await super().async_added_to_hass()

        @callback
        def _handle_flip(_now: datetime.datetime) -> None:
            self.async_write_ha_state()

        self.async_on_remove(
            async_track_time_change(
                self.hass, _handle_flip,
                hour=FLIP_HOUR, minute=FLIP_MINUTE, second=0,
            )
        )

    @property
    def native_value(self) -> str | None:
        items = self._display_items()
        return ", ".join(i["name"] for i in items) if items else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        items = self._display_items()
        return {
            "items":      items,
            "hero_image": next((i["image"] for i in items if i.get("image")), ""),
            "meal_type":  self._meal_type,
            "date":       self._display_date().isoformat(),
            "showing":    "tomorrow" if self._is_showing_tomorrow() else "today",
            "school":     self.coordinator.school,
            "district":   self.coordinator.district,
        }

    def _is_showing_tomorrow(self) -> bool:
        now = dt_util.now()
        flip = now.replace(hour=FLIP_HOUR, minute=FLIP_MINUTE, second=0, microsecond=0)
        return now >= flip

    def _display_date(self) -> datetime.date:
        """The next school day whose menu should be shown right now."""
        base = dt_util.now().date()
        if self._is_showing_tomorrow():
            base += datetime.timedelta(days=1)
        while base.weekday() >= 5:  # skip Sat/Sun
            base += datetime.timedelta(days=1)
        return base

    def _display_items(self) -> list[dict[str, str]]:
        if not self.coordinator.data:
            return []
        date_str = self._display_date().isoformat()
        return self.coordinator.data.get(date_str, {}).get(self._meal_type, [])
