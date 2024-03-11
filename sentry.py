import settings_handler
import event_checkin
import SHIB_session_generator
import logging
import time
import datetime
import reject_api


logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("SENTRY")



def wait_until_next_half():
    current = datetime.datetime.now()

    target = current + datetime.timedelta(minutes=30 - current.minute % 30)
    target = target.replace(second=0, microsecond=0)

    _logger.info(f"Sleeping until {target}, {(target - current).total_seconds()} seconds left")

    time.sleep((target - current).total_seconds())

settings = settings_handler.Settings()
first_run = True

while True:
    if not first_run:
        wait_until_next_half()

    first_run = False

    session_tokens = SHIB_session_generator.generate_session_token(settings)
    events, token = event_checkin.get_checkin_events_token(session_tokens["prestostudent_session"])

    if not events:
        _logger.warning("No events found")
        continue

    _logger.info("Events found")

    while any(event["status"] not in ["Present", "Present Late"] for event in events):
        _logger.info("Not all events are signed into")

        codes = reject_api.getCodes(settings, return_events=False)

        if not codes:
            _logger.warning("No codes found, waiting one minute")
            time.sleep(60)
            continue

        _logger.info("Codes found, attempting to sign in to events")

        event_checkin.try_codes(codes, session_tokens["XSRF-TOKEN"], session_tokens["prestostudent_session"])

        # TODO: Somehow wake the user up if any events are not signed into and have less than 15 minutes left
        #       event["time"] plus 45 minuets or implement finish time scraping

    _logger.info("All events are signed into")
