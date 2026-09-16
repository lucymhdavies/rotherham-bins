"""Constants for the Rotherham Bins integration."""

from datetime import timedelta

DOMAIN = "rotherham_bins"
NAME = "Rotherham Bins"
VERSION = "0.1.0"

API_BASE_URL = "https://bins.azurewebsites.net/api"
LOCAL_AUTHORITY = "Rotherham"
UPDATE_INTERVAL = timedelta(days=1)

CONF_POSTCODE = "postcode"
CONF_PREMISE_ID = "premise_id"
CONF_ADDRESS = "address"
CONF_LOCAL_AUTHORITY = "local_authority"

PLATFORMS = ("sensor",)

ATTR_ADDRESS = "address"
ATTR_BIN_TYPE = "bin_type"
ATTR_COLLECTIONS = "upcoming_collections"
ATTR_DAYS_UNTIL = "days_until_collection"
ATTR_LOCAL_AUTHORITY = "local_authority"
ATTR_POSTCODE = "postcode"
ATTR_PREMISE_ID = "premise_id"
