"""Calendar platform for Nutrislice School Menu.

Creates a single CalendarEntity — calendar.nutrislice_<school> — that HA
queries directly for events.  No external Local Calendar integration is
needed or touched; this integration is its own calendar provider.

The entity holds the coordinator's menu data in memory and returns
CalendarEvent objects filtered to the requested date range on demand.
This is the same pattern used by waste_collection_schedule and the
built-in Google Calendar integration.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import NutrisliceCoordinator

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Nutrislice calendar entity."""
    coordinator: NutrisliceCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([NutrisliceCalendar(coordinator, entry.entry_id)], False)


class NutrisliceCalendar(CoordinatorEntity[NutrisliceCoordinator], CalendarEntity):
    """A CalendarEntity that serves Nutrislice menu data directly to HA.

    HA calls async_get_events() whenever the calendar view is opened or an
    automation queries the calendar.  We build CalendarEvent objects from
    the coordinator's in-memory data — no external service calls required.
    """

    _attr_has_entity_name = True
    _attr_name = "School Menu"

    def __init__(self, coordinator: NutrisliceCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        school_display = coordinator.school.replace("-", " ").title()
        self._attr_unique_id = f"{DOMAIN}_{coordinator.district}_{coordinator.school}_calendar"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=f"{school_display} Menu",
            manufacturer="Nutrislice",
            model="School Menu",
            entry_type=DeviceEntryType.SERVICE,
        )

    # ── CalendarEntity required property ─────────────────────────────────────

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event (used to set entity state on/off)."""
        now = dt_util.now()
        today = now.date()

        for date_str in sorted(self.coordinator.data or {}):
            day_date = datetime.date.fromisoformat(date_str)
            if day_date < today:
                continue
            event = self._build_event(date_str)
            if event is not None:
                return event
        return None

    # ── CalendarEntity event range query ─────────────────────────────────────

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return all menu events that overlap the requested date range.

        Called by HA whenever the calendar UI or an automation asks for
        events in a window.  We build them fresh from coordinator data.
        """
        if not self.coordinator.data:
            return []

        events: list[CalendarEvent] = []
        for date_str, meals in self.coordinator.data.items():
            day_date = datetime.date.fromisoformat(date_str)

            # Event runs 08:00–15:00 local time
            event_start = dt_util.as_local(
                datetime.datetime.combine(day_date, datetime.time(8, 0))
            )
            event_end = dt_util.as_local(
                datetime.datetime.combine(day_date, datetime.time(15, 0))
            )

            # Filter to requested window
            if event_end < start_date or event_start > end_date:
                continue

            event = self._build_event(date_str)
            if event is not None:
                events.append(event)

        return sorted(events, key=lambda e: e.start)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_event(self, date_str: str) -> CalendarEvent | None:
        """Build a CalendarEvent for one school day, or None if no items."""
        meals = (self.coordinator.data or {}).get(date_str, {})
        breakfast: list[dict] = meals.get("breakfast", [])
        lunch:     list[dict] = meals.get("lunch", [])

        if not breakfast and not lunch:
            return None

        day_date = datetime.date.fromisoformat(date_str)
        school_display = self.coordinator.school.replace("-", " ").title()

        summary     = f"🏫 {school_display} – {_friendly_date(date_str)}"
        description = _build_description(breakfast, lunch)

        return CalendarEvent(
            summary=summary,
            start=dt_util.as_local(
                datetime.datetime.combine(day_date, datetime.time(8, 0))
            ),
            end=dt_util.as_local(
                datetime.datetime.combine(day_date, datetime.time(15, 0))
            ),
            description=description,
            location=_pick_hero_image(lunch or breakfast),
        )


# ── Formatting helpers ────────────────────────────────────────────────────────

def _friendly_date(date_str: str) -> str:
    d = datetime.date.fromisoformat(date_str)
    return d.strftime("%A, %b %-d")


def _pick_hero_image(items: list[dict]) -> str:
    return next((i["image"] for i in items if i.get("image")), "")


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
