#----------------------------------------------------------------------------#
#
# A module which contains frequently used functions for now.
#
#----------------------------------------------------------------------------#

# Modules needed
from datetime import datetime, timedelta, timezone, time, date
import shelve
from pydantic import BaseModel, Field # pydantic: https://docs.pydantic.dev/latest/
import requests
import ssl
import http.client
import urllib
from datetime import datetime
from dotenv import load_dotenv
import os
import xml.etree.ElementTree as ET
from enum import Enum
import myLogger


# The QRZ callsign API
def get_qrz_callsign_key():
  today = date.today()
  with shelve.open(filename='qrz', flag='c') as db:
    # Create our keys if one or both are missing
    if 'qrz_key_date' not in db or 'qrz_key_value' not in db:
      db["qrz_key_date"] = today
      db["qrz_key_value"] = get_qrz_key()
      myLogger.logger.info("QRZ: Key Date and Key Value created as no db")
    else:
      # See if we have to update our key or not
      if db["qrz_key_date"] != today:
        myLogger.logger.info(f"QRZ: key_value updated as day changed from {db["qrz_key_date"]} to {today}")
        db["qrz_key_date"] = today
        db["qrz_key_value"] = get_qrz_key()
      else:
        myLogger.logger.info("QRZ: No change for key_value as still on same day")
    return db["qrz_key_value"]



# Load variables from .env file, these are our "secrets" for accessing APIs
load_dotenv()

# Our enum for radio modes of interest in POTA
class Mode(str, Enum):
  SSB = 'SSB'; FT4 = 'FT4'; FT8 = 'FT8'; CW = 'CW'; C4FM = 'C4FM'

# Our enum for US States in POTA
class USState(str, Enum):
  US_AL='US-AL';US_AK='US-AK';US_AZ='US-AZ';US_AR='US-AR';US_CA='US-CA'
  US_CO='US-CO';US_CT='US-CT';US_DE='US-DE';US_FL='US-FL';US_GA='US-GA'
  US_HI='US-HI';US_ID='US-ID';US_IL='US-IL';US_IN='US-IN';US_IA='US-IA'
  US_KS='US-KS';US_KY='US-KY';US_LA='US-LA';US_ME='US-ME';US_MD='US-MD'
  US_MA='US-MA';US_MI='US-MI';US_MN='US-MN';US_MS='US-MS';US_MO='US-MO'
  US_MT='US-MT';US_NE='US-NE';US_NV='US-NV';US_NH='US-NH';US_NJ='US-NJ'
  US_NM='US-NM';US_NY='US-NY';US_NC='US-NC';US_ND='US-ND';US_OH='US-OH'
  US_OK='US-OK';US_OR='US-OR';US_PA='US-PA';US_RI='US-RI';US_SC='US-SC'
  US_SD='US-SD';US_TN='US-TN';US_TX='US-TX';US_UT='US-UT';US_VT='US-VT'
  US_VA='US-VA';US_WA='US-WA';US_WV='US-WV';US_WI='US-WI';US_WY='US-WY'
  US_DC='US-DC'

# Our class to hold POTA Spot information
# We're using the pydantic library for serializing/deserializing JSON
# The alias in the class specification below is for the API field names
# We're just renaming them for proper case
class PotaSpots(BaseModel):
  SpotId: int =  Field(..., alias='spotId')
  Activator: str =  Field(..., alias='activator')
  Frequency: float =  Field(..., alias='frequency')
  Mode: str =  Field(..., alias='mode')
  Reference: str =  Field(..., alias='reference')
  ParkName: str | None = Field(None, alias="parkName")
  SpotTime: datetime =  Field(..., alias='spotTime')
  Spotter: str =  Field(..., alias='spotter')
  Comments: str | None = Field(None, alias="comments")
  Source: str =  Field(..., alias='source')
  Invalid: str | None = Field(None, alias="invalid") # None is essentially null so handle that
  Name: str =  Field(..., alias='name')
  Location: str =  Field(..., alias='locationDesc')
  Grid4: str =  Field(..., alias='grid4')
  Grid6: str =  Field(..., alias='grid6')
  Latitude: float =  Field(..., alias='latitude')
  Longitude: float =  Field(..., alias='longitude')
  Count: int =  Field(..., alias='count')
  Expire: int =  Field(..., alias='expire')

# The POTA API is returning a naive datetime for SpotTime, that means that the timezone is NOT specified.
# As POTA uses Greenwich Mean Time (GMT) or specifically coordinated universal time, we need to specify the
# timezone as UTC without an offset, this function returns the UTC time if it's not already present and
# defaults to UTC 0 (GMT)
def _ensure_aware(dt: datetime) -> datetime:
  return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

# Rough conversion from frequency to band, cast the net very wide
# A frequency is the input from the POTA API and the amateur radio
# band is returned. Only interested in HF
# Switched to tuples based upon recommendations
def get_ham_band(value):
  frequency = float(value)
  bands = [
    (1800,   2000, "160m"),
    (3500,   4000, "80m"),
    (5300,   5500, "60m"),
    (7000,   7300, "40m"),
    (10100, 10150, "30m"),
    (14000, 14350, "20m"),
    (18000, 18200, "17m"),
    (21000, 21450, "15m"),
    (24800, 25000, "12m"),
    (28000, 29700, "10m"),
  ]
  for low, high, band in bands:
    if low <= frequency <= high:
      return band
  return f"[ERROR: Not Mapped]: {frequency}"

# Retrieves the QRZ key to use in subsequent API calls
# The key is good for 24 hours so at some point, cache this and update daily
# instead of what is being done now
# Modified based upon code suggestions
def get_qrz_key():
  QRZ_NS = {"qrz": "http://online.qrz.com"}
  QRZ_API_URL = "http://online.qrz.com/bin/xml"

  # Read from .env: Note that you HAVE to be a paying member to QRZ that includes
  # XML support to use this lookup
  params = {
    "username": os.getenv("QRZ_USERNAME"),
    "password": os.getenv("QRZ_PASSWORD")
  }
  headers = {"Accept": "application/xml"}
  response = requests.get(QRZ_API_URL, params=params, headers=headers)
  response.raise_for_status()  # Raise exception for HTTP errors
  root = ET.fromstring(response.content)
  return root.findtext(".//qrz:Key", namespaces=QRZ_NS)

# Retrieve the first and last name of the provided callsign
# Eventually will get this to return an object
# NOTE: That is a field is null, it will not be present in the xml
# See: https://www.qrz.com/XML/specifications.1.2.html
# Also modified based upon suggestions
def get_qrz_callsign_info(callsign, qrz_key):
  QRZ_NS = {"qrz": "http://online.qrz.com"}
  QRZ_API_URL = "http://online.qrz.com/bin/xml"

  # Our request to get callsign information from QRZ
  response = requests.get(
    QRZ_API_URL,
    params={"s": qrz_key, "callsign": callsign},
    headers={"Accept": "application/xml"},
    timeout=10
  )
  if response.status_code == 200:
    root = ET.fromstring(response.content)
    first_name = root.findtext(".//qrz:fname", namespaces=QRZ_NS)
    last_name = root.findtext(".//qrz:name", namespaces=QRZ_NS)
    trustee = root.findtext(".//qrz:trustee", namespaces=QRZ_NS)

    # Note that not all callsign lookups contain both the fname and name
    # for example, look at W4SPF
    if first_name and last_name:
      return f"{first_name} {last_name}"
    elif trustee:
      return trustee
    else:
      return "Not Found"
  else:
    return f"ERROR: {response.status_code}: {response.reason}"

# Sends a Pushover notification, note that the secrets need to be
# stored in the .env file.
# Also, notify is a List and list is then joined with a new line
# \n as the separator.
def send_pushover(notify = None):
  ssl._create_default_https_context = ssl._create_unverified_context
  conn = http.client.HTTPSConnection("api.pushover.net:443")
  conn.request("POST",
                   "/1/messages.json",
                       urllib.parse.urlencode({
                       "token": os.getenv('PUSHOVER_TOKEN'),
                       "user": os.getenv('PUSHOVER_USER'),
                       "sound": 'gamelan',
                       "message": "\n\n".join(notify),
             }), {"Content-type": "application/x-www-form-urlencoded"})
  response = conn.getresponse()
  if response.status != 200:
    print(f"ERROR: {response.status}: {response.reason}")
