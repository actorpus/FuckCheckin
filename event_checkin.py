import requests
from bs4 import BeautifulSoup
import logging
import datetime

import duo
import reject_api
import SHIB_session_generator
import settings_handler


HEADERS = {"User-Agent": "FuckCheckin/1.1"}
_logger = logging.getLogger("CHECKSTER")
BASETIME = datetime.datetime.now().strftime("%y %m %d ")


def get_checkin_events_token(session: dict[str: str]):
    _logger.info("Loading the checkin page")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/html",
        "Accept-Encoding": "gzip, deflate, br",
        "Cookie": f"prestostudent_session={session['prestostudent_session']}",
    }

    req: requests.Response = requests.get(
        "https://checkin.york.ac.uk/selfregistration",
        headers=headers,
    )

    req.raise_for_status()

    page = req.content.decode()
    soup = BeautifulSoup(page, "html.parser")

    title = soup.find("title").text

    if title == "Please log in to continue...":
        _logger.warning("Session expired")
        return False

    if title != "Check-In":
        _logger.warning("Unexpected page title: " + title)
        return False

    token = soup.find("meta", {"name": "csrf-token"})["content"]

    classes = soup.find_all("section", {"class": "box-typical box-typical-padding"})
    events = []

    if not classes:
        _logger.warning("No class objects found")
        return [], token

    if classes[0].text.__contains__("There is currently no activity for which you can register yourself."):
        _logger.info("No classes found")
        return [], token

    for _class in classes:
        time = _class.find_all("div", {"class": "col-md-4"})[0].text.strip()
        start, end = time.split(" - ")
        start = datetime.datetime.strptime(BASETIME + start, "%y %m %d %H:%M")
        end = datetime.datetime.strptime(BASETIME + end, "%y %m %d %H:%M")

        event = {
            "start_time": start,
            "end_time": end,
            "activity": _class.find_all("div", {"class": "col-md-4"})[1].text.strip(),
            "lecturer": _class.find_all("div", {"class": "col-md-4"})[2].text.strip(),
            "space": _class.find_all("div", {"class": "col-md-4"})[3].text.strip(),
            "status": "unknown",
            "id": _class.get(
                "data-activities-id"
            ),
        }

        options = _class.find_all("div", {"class": "selfregistration_status"})

        for o in options:
            if o.get("class")[-1] == "hidden":
                continue

            widget = o.find("div", {"class": "widget-simple-sm-bottom"})

            if widget is not None:
                event["status"] = o.find(
                    "div", {"class": "widget-simple-sm-bottom"}
                ).text.strip()

                continue

            event["status"] = "NotPresent"

            break

        events.append(event)

    return events, token


def try_code(event_id, code, session: dict[str: str], token):
    req = requests.post(
        f"https://checkin.york.ac.uk/api/selfregistration/{event_id}/present",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": "https://checkin.york.ac.uk/selfregistration",
            "Cookie": f"XSRF-TOKEN={session['XSRF-TOKEN']}; prestostudent_session={session['prestostudent_session']}",
        },
        data={
            "code": code,
            "_token": token,
        },
    )

    # TODO: Check response for success rather than just status for failure

    if req.status_code == 422:
        return False

    return True


def try_codes(codes, session: dict[str: str]):
    _logger.info("Starting code checking process")

    events, token = get_checkin_events_token(session)

    for event in events:
        if event["status"] in ["Present", "Present Late"]:
            _logger.info(
                f"Skipping event {event['activity']} as it is already marked as present"
            )
            continue

        _logger.info(f"Attempting to sign in to event {event['activity']}")

        for code in codes:
            result = try_code(event["id"], code, session, token)

            if result:
                _logger.info(f"Non failure during sign-in to event {event['activity']}")
                break

    events, _ = get_checkin_events_token(session)

    if any(event["status"] not in ["Present", "Present Late"] for event in events):
        _logger.warning("Not all events are signed into")
        return False

    _logger.info("All events are signed into")
    return True


def main():
    _logger.info("Checking for settings")
    settings = settings_handler.Settings()

    _logger.info("Checking for duo settings")
    duo.check_setup(settings)

    _logger.info("Generating session tokens")
    _session_tokens = SHIB_session_generator.generate_session_token(settings)

    _logger.info("Getting codes")
    codes = reject_api.getCodes(settings)

    if not codes:
        _logger.warning("No codes found, exiting")
        return False

    return try_codes(codes, _session_tokens)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    result = main()

    print("Finished with result:", result)
