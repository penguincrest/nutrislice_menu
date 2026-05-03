"""Calendar platform for Nutrislice School Menu.

Creates calendar.nutrislice_<school> and serves CalendarEvent objects to HA
on demand from the coordinator's in-memory data.
"""
from __future__ import annotations

import datetime
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from . import NutrisliceConfigEntry
from .const import DOMAIN
from .coordinator import NutrisliceCoordinator

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

# School-day window, used as the calendar event's start/end
EVENT_START_HOUR = 8
EVENT_END_HOUR = 15


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NutrisliceConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([NutrisliceCalendar(entry.runtime_data, entry.entry_id)])


class NutrisliceCalendar(CoordinatorEntity[NutrisliceCoordinator], CalendarEntity):
    """A CalendarEntity that serves Nutrislice menu data directly to HA."""

    _attr_has_entity_name = True
    _attr_name = "School Menu"

    def __init__(self, coordinator: NutrisliceCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        school_display = coordinator.school.replace("-", " ").title()
        self._attr_unique_id = f"{DOMAIN}_{coordinator.district}_{coordinator.school}_calendar"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=f"{school_display} Menu",
            manufacturer="Nutrislice",
            model="School Menu",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None

    @property
    def event(self) -> CalendarEvent | None:
        """Next upcoming event (drives the entity's on/off state)."""
        today = dt_util.now().date()
        return next(
            (ev for ev in self._iter_events() if ev.end.date() >= today),
            None,
        )

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return all menu events overlapping the requested range."""
        return [
            ev for ev in self._iter_events()
            if ev.end >= start_date and ev.start <= end_date
        ]

    def _iter_events(self):
        """Yield CalendarEvents for every day in coordinator data, sorted."""
        for date_str in sorted(self.coordinator.data or {}):
            if (event := self._build_event(date_str)) is not None:
                yield event

    def _build_event(self, date_str: str) -> CalendarEvent | None:
        meals = (self.coordinator.data or {}).get(date_str, {})
        breakfast = meals.get("breakfast", [])
        lunch = meals.get("lunch", [])
        if not breakfast and not lunch:
            return None

        day = datetime.date.fromisoformat(date_str)
        school_display = self.coordinator.school.replace("-", " ").title()

        return CalendarEvent(
            summary=f"🏫 {school_display} – {day.strftime('%A, %b %-d')}",
            start=dt_util.as_local(datetime.datetime.combine(day, datetime.time(EVENT_START_HOUR, 0))),
            end=dt_util.as_local(datetime.datetime.combine(day, datetime.time(EVENT_END_HOUR, 0))),
            description=_build_description(breakfast, lunch),
            location=next((i["image"] for i in (lunch or breakfast) if i.get("image")), ""),
        )


def _build_description(breakfast: list[dict], lunch: list[dict]) -> str:
    lines: list[str] = []
    if breakfast:
        lines.append("🍳 BREAKFAST")
        lines.extend(f"  • {i['name']}" for i in breakfast)
    if lunch:
        if lines:
            lines.append("")
        lines.append("🥗 LUNCH")
        lines.extend(f"  • {i['name']}" for i in lunch)
    return "\n".join(lines)
