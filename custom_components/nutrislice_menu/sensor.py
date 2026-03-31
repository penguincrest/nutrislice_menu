"""Sensor platform for Nutrislice School Menu.

Creates two sensors:
  sensor.<school>_breakfast_today
  sensor.<school>_lunch_today

State = comma-separated item names for today.
Attributes: items, hero_image, meal_type, date.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN, MENU_TYPES
from .coordinator import NutrisliceCoordinator

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from the config entry."""
    coordinator: NutrisliceCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    async_add_entities(
        [NutrisliceMenuSensor(coordinator, meal_type, entry.entry_id) for meal_type in MENU_TYPES],
        update_before_add=False,
    )


class NutrisliceMenuSensor(CoordinatorEntity[NutrisliceCoordinator], SensorEntity):
    """Sensor for today's menu items of one meal type."""

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
        self._attr_unique_id  = f"{DOMAIN}_{coordinator.district}_{coordinator.school}_{meal_type}_today"
        self._attr_name       = f"{meal_type.capitalize()} Today"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=f"{coordinator.school.replace('-', ' ').title()} Menu",
            manufacturer="Nutrislice",
            model="School Menu",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> str | None:
        items = self._today_items()
        return ", ".join(i["name"] for i in items) if items else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        items = self._today_items()
        return {
            "items":      items,
            "hero_image": next((i["image"] for i in items if i.get("image")), ""),
            "meal_type":  self._meal_type,
            "date":       datetime.date.today().isoformat(),
            "school":     self.coordinator.school,
            "district":   self.coordinator.district,
        }

    def _today_items(self) -> list[dict[str, str]]:
        if not self.coordinator.data:
            return []
        today = datetime.date.today().isoformat()
        return self.coordinator.data.get(today, {}).get(self._meal_type, [])
