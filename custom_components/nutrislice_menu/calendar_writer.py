"""Writes Nutrislice menu data into a Home Assistant calendar entity.

Idempotency strategy:
  1. List existing events over the two-week window.
  2. Delete any that start with our per-school ownership prefix.
  3. Create fresh events.

Using a per-school prefix means multiple schools can safely share a single
calendar without clobbering each other's events.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

WEEKS_AHEAD = 2


def _event_prefix(district: str, school: str) -> str:
    """Return the ownership marker embedded in event summaries."""
    return f"🏫 {school.replace('-', ' ').title()} ({district.upper()}) –"


async def write_calendar_events(
    hass: HomeAssistant,
    calendar_entity_id: str,
    menu_data: dict[str, Any],
    district: str = "",
    school: str = "",
) -> None:
    """Idempotently write one calendar event per school day in menu_data."""
    prefix = _event_prefix(district, school)

    today = datetime.date.today()
    range_start = _week_start(today)
    range_end = range_start + datetime.timedelta(weeks=WEEKS_AHEAD)

    await _delete_owned_events(hass, calendar_entity_id, range_start, range_end, prefix)

    for date_str, meals in sorted(menu_data.items()):
        breakfast_items: list[dict] = meals.get("breakfast", [])
        lunch_items: list[dict]     = meals.get("lunch", [])

        if not breakfast_items and not lunch_items:
            continue

        summary     = f"{prefix} {_friendly_date(date_str)}"
        description = _build_description(breakfast_items, lunch_items)
        hero_image  = _pick_hero_image(lunch_items or breakfast_items)

        try:
            await hass.services.async_call(
                "calendar",
                "create_event",
                {
                    "entity_id":        calendar_entity_id,
                    "summary":          summary,
                    "description":      description,
                    "start_date_time":  f"{date_str}T08:00:00",
                    "end_date_time":    f"{date_str}T15:00:00",
                    "location":         hero_image,
                },
                blocking=True,
            )
            _LOGGER.debug("Created calendar event: %s", summary)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Failed to create event for %s: %s", date_str, err)


async def _delete_owned_events(
    hass: HomeAssistant,
    calendar_entity_id: str,
    range_start: datetime.date,
    range_end: datetime.date,
    prefix: str,
) -> None:
    """Delete previously created events that match our ownership prefix."""
    try:
        result = await hass.services.async_call(
            "calendar",
            "list_events",
            {
                "entity_id":        calendar_entity_id,
                "start_date_time":  f"{range_start}T00:00:00",
                "end_date_time":    f"{range_end}T23:59:59",
            },
            blocking=True,
            return_response=True,
        )
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Could not list events for cleanup (non-fatal): %s", err)
        return

    events: list[dict] = result.get("events", []) if isinstance(result, dict) else []
    deleted = 0
    for event in events:
        if event.get("summary", "").startswith(prefix) and event.get("uid"):
            try:
                await hass.services.async_call(
                    "calendar",
                    "delete_event",
                    {"entity_id": calendar_entity_id, "uid": event["uid"]},
                    blocking=True,
                )
                deleted += 1
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Could not delete event uid=%s: %s", event["uid"], err)

    if deleted:
        _LOGGER.debug("Deleted %d stale event(s) from %s", deleted, calendar_entity_id)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _week_start(ref: datetime.date) -> datetime.date:
    return ref - datetime.timedelta(days=ref.weekday())


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
