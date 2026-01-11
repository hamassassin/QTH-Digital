import logging
import logging.handlers

# You must have a logs directory in the root of your application
handler = logging.handlers.TimedRotatingFileHandler(
    filename="./logs/pota_search.log",          # current log file
    when="midnight",            # rotate when the clock hits 00:00
    interval=1,                 # every 1 day
    backupCount=30,             # keep last 30 archives (delete older)
    utc=False,                  # use local time (set True if you prefer UTC)
    encoding="utf-8",
)

# Optional: give the rotated files a nice suffix (e.g. 2024‑12‑31.log)
handler.suffix = "%Y-%m-%d"      # will produce: pota_search.log.2024-12-31

formatter = logging.Formatter(
    fmt="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
handler.setFormatter(formatter)

logger = logging.getLogger(__name__)   # or use "root" if you prefer
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Log to the console as well so we know what's going on without
# looking at the file
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
