from datetime import timedelta

DOMAIN = "google_phonebook"
PLATFORMS = ["sensor"]

CONF_COUNTRY_CODE = "country_code"
CONF_CALL_LOG_MAX_ENTRIES = "call_log_max_entries"
CONF_CALL_LOG_SENSOR_ENTRIES = "call_log_sensor_entries"

DEFAULT_COUNTRY_CODE = "49"
DEFAULT_CALL_LOG_MAX_ENTRIES = 100
DEFAULT_CALL_LOG_SENSOR_ENTRIES = 10

SERVICE_LOOKUP = "lookup"
SERVICE_LOOKUP_AND_SET = "lookup_and_set"
SERVICE_CALL_EVENT = "call_event"
SERVICE_MARK_MISSED_SEEN = "mark_missed_seen"
SERVICE_CLEAR_CALL_LOG = "clear_call_log"

EVENT_CALL_FINALIZED = "google_phonebook_call_finalized"

ATTR_PHONE_NUMBER = "phone_number"
ATTR_NUMBER_ENTITY = "number_entity"
ATTR_NAME_ENTITY = "name_entity"
ATTR_EVENT = "event"
ATTR_REMOTE = "remote"
ATTR_LOCAL = "local"
ATTR_ACTIVE_USER = "active_user"
ATTR_CALL_ID = "call_id"

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_PEOPLE_CONNECTIONS_URL = "https://people.googleapis.com/v1/people/me/connections"
GOOGLE_SCOPE = "https://www.googleapis.com/auth/contacts.readonly"

UPDATE_INTERVAL = timedelta(hours=6)

CONTACT_STORAGE_VERSION = 1
CONTACT_STORAGE_KEY_PREFIX = "google_phonebook"

CALL_STORAGE_VERSION = 1
CALL_STORAGE_KEY_PREFIX = "google_phonebook_calls"
