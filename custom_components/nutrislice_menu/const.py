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

# Substrings (case-insensitive) that, if present in an item's name, mark it as
# an entree when Nutrislice didn't categorize it.  Keep these unambiguous —
# anything that could appear in a side dish should NOT go here.
ENTREE_NAME_PATTERNS = (
    "burger",
    "sandwich",
    "pizza",
    "hot dog",
    "nuggets",
    "smackers",
    "wrap",
    "taco",
    "nachos",
    "pasta",
    "spaghetti",
    "calzone",
    "quesadilla",
)

# Config entry keys
CONF_DISTRICT = "district"
CONF_SCHOOL   = "school"

# Defaults shown in the config flow form
DEFAULT_DISTRICT = "jcps"
DEFAULT_SCHOOL   = "chenoweth"

# Service
SERVICE_SYNC_MENU = "sync_menu"
