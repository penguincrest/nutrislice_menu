"""Config flow for Nutrislice School Menu integration.

Step 1 – district: user enters their Nutrislice district slug.
         Validated live against the Nutrislice schools API.

Step 2 – school: user picks their school from a live dropdown.

No calendar entity picker — the integration creates its own calendar.
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_DISTRICT,
    CONF_SCHOOL,
    DEFAULT_DISTRICT,
    DEFAULT_SCHOOL,
    DOMAIN,
    NUTRISLICE_SCHOOLS_URL,
)

_LOGGER = logging.getLogger(__name__)


class NutrisliceMenuConfigFlow(ConfigFlow, domain=DOMAIN):
    """Two-step config flow: district → school."""

    VERSION = 1

    def __init__(self) -> None:
        self._district: str = ""
        self._schools: list[dict[str, str]] = []

    # ── Step 1: district ──────────────────────────────────────────────────────

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for the Nutrislice district slug and validate it live."""
        errors: dict[str, str] = {}

        if user_input is not None:
            district = user_input[CONF_DISTRICT].strip().lower()
            schools = await self._fetch_schools(district)

            if schools is None:
                errors[CONF_DISTRICT] = "cannot_connect"
            elif not schools:
                errors[CONF_DISTRICT] = "no_schools_found"
            else:
                self._district = district
                self._schools = schools
                return await self.async_step_school()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DISTRICT, default=DEFAULT_DISTRICT): (
                        selector.TextSelector(
                            selector.TextSelectorConfig(
                                type=selector.TextSelectorType.TEXT
                            )
                        )
                    ),
                }
            ),
            errors=errors,
        )

    # ── Step 2: school ────────────────────────────────────────────────────────

    async def async_step_school(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Pick school from a live dropdown populated from the Nutrislice API."""
        if user_input is not None:
            school_slug = user_input[CONF_SCHOOL]
            school_name = next(
                (s["name"] for s in self._schools if s["slug"] == school_slug),
                school_slug,
            )

            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"{school_name} ({self._district.upper()})",
                data={
                    CONF_DISTRICT: self._district,
                    CONF_SCHOOL:   school_slug,
                },
            )

        school_options = [
            selector.SelectOptionDict(value=s["slug"], label=s["name"])
            for s in sorted(self._schools, key=lambda s: s["name"])
        ]
        default_school = next(
            (s["slug"] for s in self._schools if s["slug"] == DEFAULT_SCHOOL),
            self._schools[0]["slug"],
        )

        return self.async_show_form(
            step_id="school",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCHOOL, default=default_school): (
                        selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=school_options,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        )
                    ),
                }
            ),
            errors={},
        )

    # ── API helper ────────────────────────────────────────────────────────────

    async def _fetch_schools(self, district: str) -> list[dict[str, str]] | None:
        """Return [{"slug": ..., "name": ...}] for the district, or None on error."""
        url = NUTRISLICE_SCHOOLS_URL.format(district=district)
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 404:
                    return []
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("District lookup failed for %r: %s", district, err)
            return None

        items = data if isinstance(data, list) else data.get("schools", [])
        return [
            {"slug": item.get("slug") or item.get("id") or "",
             "name": item.get("name") or ""}
            for item in items
            if item.get("slug") or item.get("id")
        ]
