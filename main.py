#----------------------------------------------------------------------#
# Purpose:
#   Wanted to dive into Python, so I took the following as my first
#   project:
#
#   In amateur radio there is Parks on the Air (POTA) in which you
#   "hunt" activators in different parks around the USA or the world.
#   You receive "achievement" points for making contacts across all 50
#   states and DC. I'm at my last 2 states needed to get all 50+DC:
#   I'm currently missing Hawaii and Rhode Island. I decided to make a
#   Python script that will parse the POTA API looking for activators
#   who are using digital modes (FT4 or FT8) from either of these two
#   states. If an activator is found, and their latest spot occurred in
#   the last 5 minutes, then a Pushover notification is sent with the
#   details of the activator so I can then hunt them on the reported
#   band and hopefully get them into my log as a confirmed QSO and
#   wrap a bow on my 50 states
#
#   This task (and others) will be orchestrated by Prefect
#   (https://prefect.io) which will be running in a Docker container as
#   that's another piece of technology I'd like to begin using so,
#   there you have it, Happy hunting, feel free to adapt this script
#   in any way you see fit
#
# Three APIs are used:
#   POTA (Parks on the Air): Free API
#   QRZ: Have to be a paid XML subscriber to use
#   Pushover: Used for notifications
#
# NOTE: You need to create an .env file in the root of your project that
#       contains the secrets.  Remember, if in git, add .gitignore that
#       includes .env in it, don't want secrets in git!
#
#   PUSHOVER_TOKEN=REPLACE_WITH_TOKEN
#   PUSHOVER_USER=REPLACE_WITH_USER
#   QRZ_USERNAME=REPLACE WITH USERNAME
#   QRZ_PASSWORD=REPLACE WITH PASSWORD
#
# Also, the file datum.py includes helper functions and definitions
#
# All parks in CSV, make a service out of this at some point
# https://pota.app/all_parks.csv
#
# NOTE: There is next to no error checking going on.
#----------------------------------------------------------------------#

# Modules of interest
from datetime import datetime, timedelta, timezone
import time
import requests # https://pypi.org/project/requests/
from typing import List, Set
import datum # Import datum.py
import logging

# Constants
POTA_SEARCH_MINUTES = int(10)


logger = logging.getLogger(__name__)

logging.basicConfig(
    filename='pota_search.log',
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')
logger.info('-----------------------------------------------------')

# Make a GET reqeust to the activator spot service
pota_response = requests.get("https://api.pota.app/spot/activator/")

# Make sure we were successful in our GET
if pota_response.status_code == 200:

  # GPut our response in a List
  spots:List[datum.PotaSpots] = [datum.PotaSpots(**spot) for spot in pota_response.json()]

  logger.info(f"Found a total of {len(spots)} unfiltered spots")

  # Our search criteria
  needed_states = {datum.USState.US_RI, datum.USState.US_HI}
  wanted_modes = {datum.Mode.FT4, datum.Mode.FT8}
  now = datetime.now(timezone.utc) # Recall that POTA uses GMT (UTC 0) so adjust our current datetime to that
  # Interested in spots that happened within the last POTA_SEARCH_MINUTES
  cutoff = now - timedelta(minutes=POTA_SEARCH_MINUTES)

  # Filter down the complete POTA spot list to include only those we are interested in
  spots_found = [
      s for s in spots
      if s.Location in needed_states and
         s.Mode in wanted_modes and
         datum._ensure_aware(s.SpotTime) >= cutoff
  ]

  logger.info(f"Found {len(spots_found)} spots matching search criteria")

  # Well, do we have any spots in our filtered list?
  if spots_found:

    # Sort our lists of spots by time descending so we can see the most recent first
    spots_found.sort(key=lambda x: x.SpotTime, reverse=True)

    # An empty list to hold our individual spots notifications
    spots_detail = []

    # Grab our key for the QRZ API call, no need to grab it repeatedly
    # Will need to store this key as it's good for 24-hours
    qrz_key = datum.get_qrz_key()

    # Piece together our notification
    for spot_found in spots_found:
      # Handle this better as we are getting a naive datetime from the POTA API so fix that
      difference = now - datum._ensure_aware(spot_found.SpotTime)
      spots_detail.append(
        f"[{spot_found.Location} {spot_found.Mode} "
        f"{spot_found.Reference}] "
        f"{spot_found.Activator}, "
        f"{datum.get_qrz_callsign_info(spot_found.Activator, qrz_key)}, "
        f"was at {spot_found.Name} "
        f"on {datum.get_ham_band(spot_found.Frequency)} (-"
        f"{time.strftime("%M:%S", time.gmtime(difference.total_seconds()))})")
      logger.info(spots_detail[-1]);

    # Send off our Pushover notification
    datum.send_pushover(spots_detail)

# Ruh-roh Scooby, we couldn't GET the data
else:
  print(f"ERROR: {pota_response.status_code}: {pota_response.reason}")
  logger.error(f"ERROR: {pota_response.status_code}: {pota_response.reason}")

logger.info('-----------------------------------------------------')
logger.info('')
