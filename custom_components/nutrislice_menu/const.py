"""Constants for the Nutrislice School Menu integration."""

DOMAIN = "nutrislice_menu"

# Nutrislice API
NUTRISLICE_API_URL = (
    "https://{district}.api.nutrislice.com"
    "/menu/api/weeks/school/{school}"
    "/menu-type/{menu_type}/{year}/{month:02d}/{day:02d}/"
)

# Used to validate the district slug exists before finishing config flow
NUTRISLICE_SCHOOLS_URL = (
    "https://{district}.api.nutrislice.com/menu/api/schools/?format=json"
)

MENU_TYPES = ("breakfast", "lunch")

# Food categories we surface; empty string catches uncategorised items
KEEP_CATEGORIES = {"entree", "side", "fruit", "vegetable", "grain", "protein", ""}

# Config entry keys
CONF_DISTRICT        = "district"
CONF_SCHOOL          = "school"
CONF_CALENDAR_ENTITY = "calendar_entity"

# Defaults shown in the config flow form
DEFAULT_DISTRICT         = "jcps"
DEFAULT_SCHOOL           = "chenoweth"
DEFAULT_CALENDAR_ENTITY  = "calendar.school_menu"

# hass.data keys
DATA_COORDINATOR     = "coordinator"
DATA_CALENDAR_ENTITY = "calendar_entity"

# Service
SERVICE_SYNC_MENU = "sync_menu"
