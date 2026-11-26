"""Constants for BKW Dynamic Tariffs."""
from datetime import timedelta
DOMAIN = "bkw_dynamic_tariffs"
NAME = "BKW Dynamic Tariffs"
API_URL = "https://api.bkw.ch/api/dyntariffs/v1/Tariffs/energyreturn"
CONF_HIGH = "high_threshold"
CONF_LOW = "low_threshold"
DEFAULT_HIGH = 0.15
DEFAULT_LOW = 0.05
MIN_THRESHOLD = -10.0
MAX_THRESHOLD = 10.0
PRICE_UNIT = "CHF/kWh"
UPDATE_INTERVAL = timedelta(hours=12)
REQUEST_TIMEOUT = 30
