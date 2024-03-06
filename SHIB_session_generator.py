import logging
import requests
from bs4 import BeautifulSoup
from pprint import pprint
import json
import duo


def generate_session_token(settings):
    logger = logging.getLogger("SessionGenerator")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/html",
        "Accept-Encoding": "gzip, deflate, br",
    }

    logger.info("Loading initial page to initialise session and grab csrf token")

    session = requests.Session()

    req: requests.Response = session.get(
        "https://checkin.york.ac.uk/selfregistration",
        headers=headers,
    )

    req.raise_for_status()

    soup = BeautifulSoup(req.content.decode(), "html.parser")

    # find form
    form = soup.find("form", {"name": "login_form"})

    # get the csrf token from the hidden input
    token = form.find("input", {"name": "csrf_token"}).get("value")

    logger.info("Submitting username and password to grab duo session token")

    filled_form = {
        "j_username": settings.username,
        "j_password": settings.password,
        "csrf_token": token,
        "_eventId_proceed": "",
    }

    req: requests.Response = session.post(
        "https://shib.york.ac.uk" + form.get("action"),
        headers=headers,
        data=filled_form,
    )

    req.raise_for_status()

    soup = BeautifulSoup(req.content.decode(), "html.parser")

    duo_iframe = soup.find("iframe", {"id": "duo_iframe"})

    csrf_token = soup.find("input", {"name": "csrf_token"}).get("value")

    logger.info("Fetching duo frame to get APP and device defaults")
    # Get the initial iframe, contains defaults for device search request

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/html",
        "Accept-Encoding": "gzip, deflate, br",
        "Host": duo_iframe.get("data-host"),
        "Referer": "https://shib.york.ac.uk/",
        "Sec-Fetch-Dest": "iframe",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
    }

    # some bollocks about :app afterwards it does not like (2 hours to find problem)
    tx, app = duo_iframe.get("data-sig-request").split(":")
    # AH THE APP IS NEEDED

    url = (
        "https://"
        + duo_iframe.get("data-host")
        + "/frame/web/v1/auth?tx="
        + tx
        + "&parent="
        + duo_iframe.get("data-post-action")
        + "&v=2.6"
    )

    req = session.get(
        url,
        headers=headers,
    )
    req.raise_for_status()

    soup = BeautifulSoup(req.content.decode(), "html.parser")

    # get the hidden inputs into a form type

    data = {}

    for input in soup.find_all("input"):
        data[input.get("name")] = input.get("value")

    logger.info("Submitting device information to DUO")

    data["screen_resolution_width"] = "1920"
    data["screen_resolution_height"] = "1080"
    data["color_depth"] = "24"
    data["has_touch_capability"] = "false"
    data["is_cef_browser"] = "false"
    data["is_ipad_os"] = "false"
    data["is_user_verifying_platform_authenticator_available"] = "false"
    data["react_support"] = "true"

    req = session.post(
        url,
        data=data,
        headers=headers,
    )

    req.raise_for_status()

    soup = BeautifulSoup(req.content.decode(), "html.parser")

    logger.info("Aggregating DUO session token")

    data = {}

    for input in soup.find_all("input"):
        if input.get("name") not in [
            "sid",
            "akey",
            "txid",
            "response_timeout",
            "parent",
            "duo_app_url",
            "eh_service_url",
            "eh_download_link",
            "_xsrf",
            "is_silent_collection",
            "has_chromium_http_feature",
        ]:
            continue

        data[input.get("name")] = input.get("value")

    sid = data["sid"]

    session.post(
        url,
        data=data,
        headers=headers,
    ).raise_for_status()

    logger.info("Submitting generated duo code to DUO")

    code = duo.generate_code()

    data = {
        "sid": sid,
        "device": "phone1",
        "factor": "Passcode",
        "passcode": code,
        "out_of_date": "",
        "days_out_of_date": "",
        "days_to_block": "None",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/html",
        "Accept-Encoding": "gzip, deflate, br",
        "Host": duo_iframe.get("data-host"),
        "Referer": f"https://{duo_iframe.get('data-host')}/frame/prompt?sid={sid}",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    req = session.post(
        "https://" + duo_iframe.get("data-host") + "/frame/prompt",
        data=data,
        headers=headers,
    )

    req.raise_for_status()

    response = req.json()

    logger.info("Getting result url from DUO")

    data = {
        "sid": sid,
        "txid": response["response"]["txid"],
    }

    req = session.post(
        "https://" + duo_iframe.get("data-host") + "/frame/status",
        data=data,
        headers=headers,
    )

    req.raise_for_status()

    response = req.json()

    logger.info("Submitting DUO result to SHIB")

    data = {
        "sid": sid,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/plain",
        "Accept-Encoding": "gzip, deflate, br",
        "Prefer": "safe",
        "Referer": f"{duo_iframe.get('data-host')}/frame/prompt?sid={sid}",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "DNT": "1",
        "Origin": "https://" + duo_iframe.get("data-host"),
    }

    req = session.post(
        "https://" + duo_iframe.get("data-host") + response["response"]["result_url"],
        data=data,
        headers=headers,
    )

    req.raise_for_status()

    response = req.json()

    logger.info("Submitting APP and final csrf to SHIB")

    data = {
        "csrf_token": csrf_token,
        "_eventId": "proceed",
        "sig_response": response["response"]["cookie"] + ":" + app,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/html",
        "Accept-Encoding": "gzip, deflate, br",
        "Host": "shib.york.ac.uk",
        "Referer": "https://shib.york.ac.uk" + response["response"]["parent"],
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
    }

    req = session.post(
        "https://shib.york.ac.uk" + response["response"]["parent"],
        data=data,
        headers=headers,
    )

    req.raise_for_status()

    soup = BeautifulSoup(req.content.decode(), "html.parser")

    relay_state = soup.find("input", {"name": "RelayState"}).get("value")
    saml_response = soup.find("input", {"name": "SAMLResponse"}).get("value")
    action = soup.find("form").get("action")

    logger.info("Submitting final SAML response to SHIB, fetching session cookies")

    data = {
        "RelayState": relay_state,
        "SAMLResponse": saml_response,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/html",
        "Accept-Encoding": "gzip, deflate, br",
        "Host": "checkin.york.ac.uk",
        "Referer": "https://shib.york.ac.uk",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-site",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Origin": "https://shib.york.ac.uk",  # Lack of origin waisted 3 hours of my life, fuck the web
    }

    req = session.post(action, data=data, headers=headers)

    req.raise_for_status()

    logger.info("Refreshing session tokens using checkin")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/html",
        "Accept-Encoding": "gzip, deflate, br",
        "Prefer": "safe",
        "Referer": "https://shib.york.ac.uk/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-site",
        "Connection": "keep-alive",
    }

    req = session.get(
        "https://checkin.york.ac.uk/",
        headers=headers,
    )

    req = session.get(
        "https://checkin.york.ac.uk/selfregistration",
        headers=headers,
    )

    return {
        "prestostudent_session": session.cookies.get("prestostudent_session"),
        "XSRF-TOKEN": session.cookies.get("XSRF-TOKEN"),
    }


if __name__ == "__main__":
    import settings_handler

    _settings = settingzer.Settings()

    logging.basicConfig(level=logging.INFO)

    logging.log(logging.INFO, "Starting session token generation")

    cookies = generate_session_token(_settings)
    pprint(cookies)
