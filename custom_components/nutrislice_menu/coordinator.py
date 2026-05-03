"""DataUpdateCoordinator for Nutrislice School Menu."""
from __future__ import annotations

import datetime
import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, ENTREE_NAME_PATTERNS, MENU_TYPES, NUTRISLICE_API_URL

_LOGGER = logging.getLogger(__name__)

WEEKS_AHEAD = 2


class NutrisliceCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetches breakfast and lunch menus for a single school from Nutrislice.

    Data shape returned by _async_update_data:
    {
        "2026-04-07": {
            "breakfast": [{"name": str, "category": str, "image": str}, ...],
            "lunch":     [{"name": str, "category": str, "image": str}, ...],
        },
        ...   # one entry per weekday that has menu data
    }
    """

    def __init__(self, hass: HomeAssistant, district: str, school: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{district}_{school}",
            # No automatic polling – driven entirely by the sync_menu service
            update_interval=None,
        )
        self.district = district
        self.school = school

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch menus for this week and next week from Nutrislice."""
        today = datetime.date.today()
        week_starts = [
            _week_start(today + datetime.timedelta(weeks=i))
            for i in range(WEEKS_AHEAD)
        ]

        session = async_get_clientsession(self.hass)
        merged: dict[str, Any] = {}

        for week_start in week_starts:
            try:
                fetched = {
                    mt: await self._fetch_week(session, mt, week_start)
                    for mt in MENU_TYPES
                }
            except aiohttp.ClientError as err:
                raise UpdateFailed(
                    f"Network error fetching Nutrislice data for "
                    f"{self.district}/{self.school}: {err}"
                ) from err

            all_dates = set().union(*[d.keys() for d in fetched.values()])
            for ds in all_dates:
                day = datetime.date.fromisoformat(ds)
                if day.weekday() >= 5:   # skip weekends
                    continue
                merged[ds] = {mt: fetched[mt].get(ds, []) for mt in MENU_TYPES}

        _LOGGER.debug(
            "Nutrislice sync complete – %d days fetched for %s/%s",
            len(merged), self.district, self.school,
        )
        return merged

    async def _fetch_week(
        self,
        session: aiohttp.ClientSession,
        menu_type: str,
        week_start: datetime.date,
    ) -> dict[str, list[dict[str, str]]]:
        """Fetch one week of one menu type. Returns {date_str: [items]}."""
        url = NUTRISLICE_API_URL.format(
            district=self.district,
            school=self.school,
            menu_type=menu_type,
            year=week_start.year,
            month=week_start.month,
            day=week_start.day,
        )
        _LOGGER.debug("Fetching %s", url)

        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)

        result: dict[str, list[dict[str, str]]] = {}
        for day in data.get("days", []):
            date_str: str = day.get("date", "")
            if not date_str:
                continue
            items: list[dict[str, str]] = []
            for mi in day.get("menu_items", []):
                food: dict = mi.get("food") or {}
                name: str = (food.get("name") or "").strip()
                if not name:
                    continue
                category = (food.get("food_category") or "").lower()
                if not category and any(p in name.lower() for p in ENTREE_NAME_PATTERNS):
                    category = "entree"
                items.append({
                    "name": name,
                    "category": category,
                    "image": food.get("image_url") or food.get("default_image_url") or "",
                })
            result[date_str] = items

        return result


def _week_start(ref: datetime.date) -> datetime.date:
    """Return the Monday of the week containing ref."""
    return ref - datetime.timedelta(days=ref.weekday())
