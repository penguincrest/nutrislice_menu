"""Constants for the Nutrislice School Menu integration."""

DOMAIN = "nutrislice_menu"

# Nutrislice API
NUTRISLICE_API_URL = (
    "https://{district}.api.nutrislice.com"
    "/menu/api/weeks/school/{school}"
    "/menu-type/{menu_type}/{year}/{month:02d}/{day:02d}/"
)

# Used to validate the district slug during config flow
NUTRISLICE_SCHOOLS_URL = (
    "https://{district}.api.nutrislice.com/menu/api/schools/?format=json"
)

MENU_TYPES = ("breakfast", "lunch")

# Config entry keys
CONF_DISTRICT = "district"
CONF_SCHOOL   = "school"

# Defaults shown in the config flow form
DEFAULT_DISTRICT = "jcps"
DEFAULT_SCHOOL   = "chenoweth"

# hass.data key
DATA_COORDINATOR = "coordinator"

# Service
SERVICE_SYNC_MENU = "sync_menu"
