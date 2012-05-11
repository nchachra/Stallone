# Queue sizes
REQUEST_Q_SIZE = 15
RESULT_Q_SIZE = REQUEST_Q_SIZE * 3

# Files and directories
LOG_FILENAME = 'stallone.log'
LOG_FORMAT = "%(levelname)s|%(asctime)s|%(name)s|%(process)s %(msg)s"
MAIN_LOGGER_NAME = "Stallone"
LOG_DIR = "logs"
# Directory for firefox profiles
PROFILE_DIR = "firefox_profiles"

# Constants
PAGE_TIMEOUT=180
# Alarm is fired if a visit doesn't complete in ALARM_TIME
ALARM_TIME=15*60
# Restart firefox every so many visits
MAX_BROWSER_VISITS_PER_RESTART=50

#Status codes
PAGE_TIMEOUT_ST = 'tim'
PROXY_ERR_ST = 'prx'
FIREFOX_ERR_ST='err'

