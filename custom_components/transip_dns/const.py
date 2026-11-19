"""Constants for the TransIP Dynamic DNS integration.

Single source of truth for naming: the integration name, the panel URL and
the custom element name are defined here and nowhere else. Renaming the
integration is a change in this file only.
"""
from datetime import timedelta

DOMAIN = "transip_dns"

# Naming (keep every user visible name out of the code and the frontend)
INTEGRATION_NAME = "TransIP DNS"
PANEL_URL_PATH = "transip-dns"
PANEL_ELEMENT = "transip-dns-panel"
PANEL_ICON = "mdi:dns"
PANEL_FOLDER = "panel"
PANEL_ASSET_BASE = f"/{DOMAIN}_panel"
PANEL_JS_NAME = f"{PANEL_ELEMENT}.js"

# Config entry / options keys
CONF_LOGIN = "login"
CONF_PRIVATE_KEY = "private_key"
CONF_RECORDS = "records"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_NOTIFY_PERSISTENT = "notify_persistent"
CONF_NOTIFY_EVENT = "notify_event"
CONF_NOTIFY_TARGETS = "notify_targets"
CONF_PANEL_ENABLED = "panel_enabled"
CONF_PANEL_SIDEBAR = "panel_sidebar"

DEFAULT_NOTIFY_PERSISTENT = True
DEFAULT_NOTIFY_EVENT = True
DEFAULT_NOTIFY_TARGETS: list[str] = []
# Off by default: switching it on is what replaces the options dialog with
# the panel, so nothing changes for an existing installation until asked.
DEFAULT_PANEL_ENABLED = False
DEFAULT_PANEL_SIDEBAR = False

EVENT_DNS_UPDATED = "transip_dns_updated"

CONF_DOMAIN_NAME = "domain"
CONF_RECORD_NAME = "name"
CONF_RECORD_TYPE = "record_type"

RECORD_TYPES = ["A", "AAAA"]
DEFAULT_RECORD_TYPE = "A"
DEFAULT_RECORD_NAME = "@"

DEFAULT_UPDATE_INTERVAL_MINUTES = 10
MIN_UPDATE_INTERVAL_MINUTES = 2
MAX_UPDATE_INTERVAL_MINUTES = 1440
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=DEFAULT_UPDATE_INTERVAL_MINUTES)

# TransIP API
API_BASE_URL = "https://api.transip.nl/v6"
API_AUTH_PATH = "/auth"
API_TEST_PATH = "/api-test"
API_DNS_PATH = "/domains/{domain}/dns"

TOKEN_LABEL = "home-assistant-dns-updater"
TOKEN_EXPIRATION_TIME = "30 minutes"

# Public IP lookup services (tried in order, first success wins)
IPV4_LOOKUP_URLS = [
    "https://api.ipify.org?format=json",
    "https://api4.ipify.org?format=json",
]
IPV6_LOOKUP_URLS = [
    "https://api6.ipify.org?format=json",
]

# Persistent storage for IP history (survives restarts)
STORAGE_VERSION = 1
STORAGE_KEY = DOMAIN
# How many IP changes to keep per address family.
HISTORY_LENGTH = 20

# Services
SERVICE_REFRESH = "refresh"
SERVICE_SET_PANEL_ENABLED = "set_panel_enabled"
ATTR_ENABLED = "enabled"
ATTR_ENTRY_ID = "entry_id"

# Websocket commands used by the panel
WS_INFO = f"{DOMAIN}/info"
WS_DOMAINS = f"{DOMAIN}/domains"
WS_SET_RECORDS = f"{DOMAIN}/records/set"
WS_SET_OPTIONS = f"{DOMAIN}/options/set"
WS_REFRESH = f"{DOMAIN}/refresh"

ATTR_DOMAIN = "domain"
ATTR_NAME = "name"
ATTR_TYPE = "type"
ATTR_LAST_CHECKED = "last_checked"
ATTR_LAST_UPDATED = "last_updated"
ATTR_STATUS = "status"
ATTR_PREVIOUS_IP = "previous_ip"
ATTR_CHANGED_AT = "changed_at"

STATUS_OK = "ok"
STATUS_UPDATED = "updated"
STATUS_NOT_FOUND = "record_not_found"
STATUS_ERROR = "error"
