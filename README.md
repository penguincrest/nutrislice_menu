# Nutrislice School Menu

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/penguincrest/nutrislice_menu.svg?style=for-the-badge)](https://github.com/penguincrest/nutrislice_menu/releases)
[![License](https://img.shields.io/github/license/penguincrest/nutrislice_menu.svg?style=for-the-badge)](LICENSE)

A Home Assistant custom integration that pulls **breakfast and lunch menus** from any school using [Nutrislice](https://nutrislice.com) and:

- Creates **two sensor entities** with today's menu items and food images
- Registers a **`nutrislice_menu.sync_menu` service** that fetches the upcoming week's menus and writes them as events to any HA calendar
- Supports **multiple schools** — add one config entry per school

> **Scheduling is up to you.** Call `nutrislice_menu.sync_menu` from a HA automation whenever you want a refresh. No background polling.

---

## Installation

### Via HACS (recommended)

1. In HACS, click **+ Explore & Download Repositories**
2. Search for **Nutrislice School Menu** — or add this repo as a custom repository:
   - HACS → ⋮ → Custom Repositories → paste your repo URL → Category: Integration
3. Click **Download**
4. Restart Home Assistant

### Manual

Copy the `custom_components/nutrislice_menu/` folder into your HA config at:
```
/config/custom_components/nutrislice_menu/
```
Then restart Home Assistant.

---

## Setup

### 1. Create a Local Calendar

Go to **Settings → Integrations → + Add Integration → Local Calendar**.  
Name it **School Menu** → entity becomes `calendar.school_menu`.

### 2. Add the integration

[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=nutrislice_menu)

Or go to **Settings → Integrations → + Add Integration → Nutrislice School Menu**.

**Step 1 – District slug**

Enter your district's Nutrislice subdomain. If your school's menu URL is `https://jcps.nutrislice.com/menu/...`, the slug is `jcps`.

The integration validates this live and fetches your district's school list.

**Step 2 – School & Calendar**

Pick your school from the dropdown (populated from Nutrislice) and choose the calendar entity to write events into.

Repeat these steps to add additional schools.

### 3. Create an automation to sync menus

The integration never syncs automatically. Create an automation that calls `nutrislice_menu.sync_menu`:

```yaml
- alias: "School menu – sync Sunday evening"
  trigger:
    - platform: time
      at: "20:00:00"
  condition:
    - condition: time
      weekday: [sun]
  action:
    - service: nutrislice_menu.sync_menu
```

You can also trigger it manually at any time from  
**Developer Tools → Services → nutrislice_menu.sync_menu → Call Service**.

---

## Entities

Two sensors are created per configured school:

| Entity | Description |
|---|---|
| `sensor.<school>_breakfast_today` | Today's breakfast items (comma-separated) |
| `sensor.<school>_lunch_today` | Today's lunch items (comma-separated) |

### Sensor attributes

| Attribute | Description |
|---|---|
| `items` | Full list of `{name, category, image}` dicts |
| `hero_image` | URL of the first food image (useful for notifications) |
| `meal_type` | `breakfast` or `lunch` |
| `date` | ISO date string for today |
| `school` | School slug |
| `district` | District slug |

---

## Service: `nutrislice_menu.sync_menu`

Fetches this week's and next week's menus from Nutrislice, updates the sensor entities, and creates/replaces calendar events.

**Optional field:**

| Field | Description |
|---|---|
| `entry_id` | Limit sync to one school. If omitted, all configured schools sync. |

---

## Dashboard card

```yaml
type: vertical-stack
title: "🏫 School Menu"
cards:
  - type: markdown
    title: "🍳 Breakfast"
    content: >
      {% set items = state_attr('sensor.chenoweth_breakfast_today', 'items') %}
      {% if items %}
        {% for item in items %}
          - **{{ item.name }}**{% if item.image %}
          ![]( {{- item.image -}} ){width=80}{% endif %}
        {% endfor %}
      {% else %}
        _No data – run sync_menu service_
      {% endif %}
  - type: markdown
    title: "🥗 Lunch"
    content: >
      {% set items = state_attr('sensor.chenoweth_lunch_today', 'items') %}
      {% if items %}
        {% for item in items %}
          - **{{ item.name }}**{% if item.image %}
          ![]( {{- item.image -}} ){width=80}{% endif %}
        {% endfor %}
      {% else %}
        _No data – run sync_menu service_
      {% endif %}
  - type: calendar
    entities:
      - calendar.school_menu
    initial_view: dayGridWeek
```

---

## Finding your district slug

1. Go to [nutrislice.com](https://nutrislice.com) and find your school
2. The URL will look like `https://<district>.nutrislice.com/menu/<school>/...`
3. The `<district>` part is what you enter in the config flow

**Common examples:**

| District | Slug |
|---|---|
| Jefferson County Public Schools (KY) | `jcps` |
| Pleasant Valley USD (CA) | `pleasantvalley` |
| Souderton Area SD (PA) | `soudertonsd` |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Could not connect" in setup | Check the district slug against your Nutrislice URL |
| No events in calendar | Run sync_menu from Developer Tools; check HA logs for errors |
| Duplicate events | Shouldn't happen – each sync deletes old events first. If it does, delete all `🏫` events manually and re-sync |
| Sensors show `None` | Today might be a weekend or holiday; check the coordinator data in Dev Tools → States |

---

## Contributing

Issues and PRs welcome at [github.com/penguincrest/nutrislice_menu](https://github.com/penguincrest/nutrislice_menu).
