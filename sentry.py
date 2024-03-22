import atexit
import datetime
import logging
import logging.handlers
import time
import winsound

import SHIB_session_generator
import event_checkin
import reject_api
import settings_handler

_file_log = logging.handlers.TimedRotatingFileHandler(
    "sentry.log", when="midnight", backupCount=7
)
_file_log.setLevel(logging.DEBUG)
_file_log.setFormatter(
    logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
)

_console_log = logging.StreamHandler()
_console_log.setLevel(logging.INFO)


logging.basicConfig(level=logging.DEBUG, handlers=[_file_log, _console_log])

_logger = logging.getLogger("Sentry")



def sound_alarm():
    # Feel free to implement your own alarm (could send request to webhook or call your phone)
    while True:
        winsound.Beep(1000, 1000)
        time.sleep(1)


# Using atexit as a way to handle unexpected exits as it cannot be stopped by any form of exception
# Other than your server dying I guess but that's not my fault :)
@atexit.register
def unexpected_exit():
    _logger.critical("Unexpected exit, could be result of exception, starting alarm")

    sound_alarm()

_logger.info("Exit alarm registered")


def wait_until_next_half():
    current = datetime.datetime.now()

    target = current + datetime.timedelta(minutes=30 - current.minute % 30)
    target = target.replace(second=0, microsecond=0)

    _logger.info(f"Sleeping until {target}, {(target - current).total_seconds().__floor__()} seconds left")

    try:
        time.sleep((target - current).total_seconds())

    except KeyboardInterrupt:
        _logger.info("User interrupted during sleep, unregistering alarm")

        atexit.unregister(unexpected_exit)
        exit(0)


settings = settings_handler.Settings()
first_run = True

while True:
    if not first_run:
        wait_until_next_half()

    first_run = False

    session_tokens = SHIB_session_generator.generate_session_token(settings)
    events, token = event_checkin.get_checkin_events_token(session_tokens)

    if not events:
        _logger.info("No events found")
        continue

    _logger.info(f"Events found: {', '.join([event['start_time'].strftime('%H:%M ') + event['activity'] for event in events])}")

    while any(event["status"] not in ["Present", "Present Late"] for event in events):
        _logger.debug("Not all events are signed into")

        codes = reject_api.getCodes(settings, return_events=False)

        if not codes:
            _logger.warning("No codes found, waiting one minute")
            time.sleep(60)
            # No point refreshing the events as no codes means no possible change in state
            continue

        _logger.info(f"Codes found: {', '.join([str(a) for a in codes])}, attempting to sign in to events")

        # event_checkin.try_codes(codes, session_tokens["XSRF-TOKEN"], session_tokens["prestostudent_session"])
        event_checkin.try_codes(codes, session_tokens)

        events, token = event_checkin.get_checkin_events_token(session_tokens["prestostudent_session"])

        # Check for any almost over
        if any(
            event["end_time"] - datetime.datetime.now() < datetime.timedelta(minutes=15)
            for event in events
        ):
            _logger.error("One or more events have less than 15 minutes left, unregistering and starting alarm")

            atexit.unregister(unexpected_exit)
            sound_alarm()
            exit()

    _logger.debug("All events are signed into")
