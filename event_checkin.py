import time
import requests
import json
import os
from bs4 import BeautifulSoup
from pprint import pprint
import sys
import logging

import duo
import reject_api
import SHIB_session_generator
import settings_handler


HEADERS = {"User-Agent": "FuckCheckin/1.1"}
_logger = logging.getLogger("CHECKSTER")


def get_checkin_events_token(session):
    _logger.info("Loading the checkin page")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/html",
        "Accept-Encoding": "gzip, deflate, br",
        "Cookie": f"prestostudent_session={session}",
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

    classes = soup.find_all("div", {"class": "text-block bs"})
    events = []

    for _class in classes:
        event = {
            "time": _class.find_all("div", {"class": "col-md-4"})[0].text.strip(),
            "activity": _class.find_all("div", {"class": "col-md-4"})[1].text.strip(),
            "lecturer": _class.find_all("div", {"class": "col-md-4"})[2].text.strip(),
            "space": _class.find_all("div", {"class": "col-md-4"})[3].text.strip(),
            "status": "unknown",
            "id": _class.find("div", {"attr": "data-activities-id"}).get(
                "data-activities-id"
            ),
        }

        options = _class.find_all("div", {"class": "selfregistration_status"})

        for o in options:
            if o.get("class")[-1] == "hidden":
                continue

            event["status"] = o.find(
                "div", {"class": "widget-simple-sm-bottom"}
            ).text.strip()

            break

        events.append(event)

    return events, token


def try_code(event_id, code, xsrf_token, session, token):
    req = requests.post(
        f"https://checkin.york.ac.uk/api/selfregistration/{event_id}/present",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": "https://checkin.york.ac.uk/selfregistration",
            "Cookie": f"XSRF-TOKEN={xsrf_token}; prestostudent_session={session}",
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


def try_codes(codes, xsrf_token, session):
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
            result = try_code(event["id"], code, xsrf_token, session, token)

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
    settings = settingzer.Settings()

    _logger.info("Checking for duo settings")
    duo.check_setup(settings)

    _logger.info("Generating session tokens")
    _session_tokens = SHIBinator.generate_session_token(settings)
    xsrf_token = _session_tokens["XSRF-TOKEN"]
    session = _session_tokens["prestostudent_session"]

    _logger.info("Getting codes")
    codes = rejector.getCodes(settings)

    if not codes:
        _logger.warning("No codes found, exiting")
        return False

    return try_codes(codes, xsrf_token, session)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    result = main()

    print("Finished with result:", result)
