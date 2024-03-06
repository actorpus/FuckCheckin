import os.path
import requests
from bs4 import BeautifulSoup
import json
from Crypto.PublicKey import RSA
import base64
import logging
import pyotp
import requests.utils

DUO_KEYS_FILE = "duo_keys.DONOTSHARE.json"

_logger = logging.getLogger("DUO")


def generate_code():
    with open(DUO_KEYS_FILE, "r") as file:
        settings = json.load(file)

    secret = settings["t"]
    count = settings["c"]

    hotp = pyotp.HOTP(secret)
    code = hotp.at(count)

    _logger.info(f"Code generation C{count}c{code}")

    settings["c"] += 1

    with open(DUO_KEYS_FILE, "w") as j:
        json.dump(settings, j)

    return code


def export_code(settings):
    import pyqrcode

    with open(DUO_KEYS_FILE, "r") as file:
        duo_keys = json.load(file)

    qr = pyqrcode.create(
        f'otpauth://hotp/DUOKEY?secret={duo_keys["t"].strip("=")}&issuer={settings.username}&counter={duo_keys["c"]}'
    )
    print(qr.terminal(quiet_zone=4))


def generate_duo_keys(settings):
    session = requests.Session()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/html",
        "Accept-Encoding": "gzip, deflate, br",
    }

    _logger.info("Loading initial page to initialise session and grab csrf token")

    req = session.get(
        "https://duo.york.ac.uk/manage",
        headers=headers,
    )

    req.raise_for_status()

    soup = BeautifulSoup(req.content.decode(), "html.parser")

    form = soup.find("form", {"name": "login_form"})

    csrf_token = form.find("input", {"name": "csrf_token"}).get("value")

    filled_form = {
        "j_username": settings.username,
        "j_password": settings.password,
        "csrf_token": csrf_token,
        "_eventId_proceed": "",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/html",
        "Accept-Encoding": "gzip, deflate, br",
        "Host": "shib.york.ac.uk",
        "Referer": req.url,
        "Origin": "https://shib.york.ac.uk",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
    }

    _logger.info("Submitting username and password to generate SAMl response")

    req = session.post(
        "https://shib.york.ac.uk" + form.get("action"),
        headers=headers,
        data=filled_form,
    )

    req.raise_for_status()

    soup = BeautifulSoup(req.content.decode(), "html.parser")

    action = soup.find("form").get("action")
    relay_state = soup.find("input", {"name": "RelayState"}).get("value")
    SAMLResponse = soup.find("input", {"name": "SAMLResponse"}).get("value")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/html",
        "Accept-Encoding": "gzip, deflate, br",
        # "Host": "auth.aws.york.ac.uk",  # the internet works in weird ways sometimes
        "Origin": "https://shib.york.ac.uk",
        "Referer": "https://shib.york.ac.uk",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-User": "?1",
        "Sec-GPC": "1",
        "Prefer": "safe",
        "DNT": "1",
    }

    data = {
        "RelayState": relay_state,
        "SAMLResponse": SAMLResponse,
    }

    _logger.info("Submitting SAML response to grab duo session token")

    req = session.post(action, headers=headers, data=data)

    req.raise_for_status()

    soup = BeautifulSoup(req.content.decode(), "html.parser")

    script = soup.findAll("script")
    script = [s for s in script if "Duo.init" in s.text][0].text

    host = script.split("host': '")[1].split("'")[0]
    sig_request = script.split("sig_request': '")[1].split("'")[0]

    tx_token, app_token = sig_request.split(":")

    device_info = {
        "tx": tx_token,
        "parent": "https://duo.york.ac.uk/manage",
        "version": "",
        "akey": "",
        "has_session_trust_analysis_feature": "False",
        "session_trust_extension_id": "",
        "java_version": "",
        "flash_version": "",
        "screen_resolution_width": "1920",
        "screen_resolution_height": "1080",
        "extension_instance_key": "",
        "color_depth": "24",
        "has_touch_capability": "false",
        "ch_ua_error": "",
        "client_hints": "",
        "is_cef_browser": "false",
        "is_ipad_os": "false",
        "is_ie_compatibility_mode": "",
        "is_user_verifying_platform_authenticator_available": "false",
        "user_verifying_platform_authenticator_available_error": "",
        "acting_ie_version": "",
        "react_support": "true",
        "react_support_error_message": "",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/html",
        "Accept-Encoding": "gzip, deflate, br",
        "Host": host,
        "Origin": "https://" + host,
        "Referer": "https://"
        + host
        + "/frame/web/v1/auth?tx="
        + tx_token
        + "&parent=https://duo.york.ac.uk/manage&v=2.6",
        "Sec-Fetch-Dest": "iframe",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-GPC": "1",
        "Prefer": "safe",
        "DNT": "1",
    }

    _logger.info("Submitting device information to DUO")

    req = session.post(
        "https://"
        + host
        + "/frame/web/v1/auth?tx="
        + tx_token
        + "&parent=https://duo.york.ac.uk/manage&v=2.6",
        headers=headers,
        data=device_info,
    )

    req.raise_for_status()

    soup = BeautifulSoup(req.content.decode(), "html.parser")

    things = [
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
    ]

    data = {}

    for thing in things:
        data[thing] = soup.find("input", {"name": thing}).get("value")

    _logger.info("Submitting device information to DUO (2)")

    req = session.post(
        "https://"
        + host
        + "/frame/web/v1/auth?tx="
        + tx_token
        + "&parent=https://duo.york.ac.uk/manage&v=2.6",
        headers=headers,
        data=data,
    )

    req.raise_for_status()

    soup = BeautifulSoup(req.content.decode(), "html.parser")

    sid_token = soup.find("input", {"name": "sid"}).get("value")
    xsrf_token = soup.find("input", {"name": "_xsrf"}).get("value")

    data = {
        "sid": sid_token,
        "device": "phone1",
        "factor": "Duo Push",  # Not Duo+Push as the trace suggests
        "out_of_date": "",
        "days_out_of_date": "",
        "days_to_block": "None",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/plain",
        "Accept-Encoding": "gzip, deflate, br",
        "Host": host,
        "Origin": "https://" + host,
        "Referer": "https://" + host + "/frame/prompt?sid=" + sid_token,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Sec-GPC": "1",
        "DNT": "1",
    }

    _logger.info("Generating Duo Push request")

    req = session.post(
        "https://" + host + "/frame/prompt",
        headers=headers,
        data=data,
    )

    req.raise_for_status()

    response = req.json()

    txid_token = response["response"]["txid"]

    data = {
        "sid": sid_token,
        "txid": txid_token,
    }

    _logger.info("Getting status of Duo Push")

    req = session.post(
        "https://" + host + "/frame/status",
        headers=headers,
        data=data,
    )

    req.raise_for_status()

    print("Accept the duo push")

    _logger.info("Waiting for Duo Push to be accepted, (status request)")

    req = session.post(
        "https://" + host + "/frame/status",
        headers=headers,
        data=data,
    )

    req.raise_for_status()

    response = req.json()

    if response["response"]["result"] != "SUCCESS":
        _logger.warning("Failed to get status, Duo Push may not have been accepted")
        return False

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/html",
        "Accept-Encoding": "gzip, deflate, br",
        "Host": host,
        "Referer": "https://"
        + host
        + "/frame/enroll/install_mobile_app?sid="
        + sid_token
        + "&from_settings=1",
        "Sec-Fetch-Dest": "iframe",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Sec-GPC": "1",
        "DNT": "1",
    }

    _logger.info("Activating mobile device to get qr secret")

    req = session.get(
        "https://"
        + host
        + "/frame/enroll/mobile_activate?sid="
        + sid_token
        + "&platform=Android&_xsrf="
        + xsrf_token,
        headers=headers,
    )

    soup = BeautifulSoup(req.content.decode(), "html.parser")

    qr_image = soup.findAll("img")
    qr_image = [i for i in qr_image if "frame/qr?value=" in i.get("src")][0]
    code = qr_image.get("src").split("frame/qr?value=")[1].split("-")[0]

    headers = {
        "User-Agent": "okhttp/2.7.5",
        "Accept": "application/json",
    }

    data = {
        "pkpush": "rsa-sha512",
        "pubkey": RSA.generate(2048).public_key().export_key("PEM").decode(),
        "jailbroken": "false",
        "architecture": "arm64",
        "region": "US",
        "app_id": "com.duosecurity.duomobile",
        "full_disk_encryption": "true",
        "passcode_status": "true",
        "platform": "Android",
        "app_version": "3.49.0",
        "app_build_number": "323001",
        "version": "11",
        "manufacturer": "unknown",
        "language": "en",
        "model": "Pixel 3a",
        "security_patch_level": "2021-02-01",
    }

    # thanks to https://github.com/revalo/duo-bypass/commit/3dd0cf08bed7e7f5fbafa75b55320372528062d1

    _logger.info("Simulating mobile activation to get Duo Keys")

    req = requests.post(
        f"https://{host}/push/v2/activation/{code}?customer_protocol=1",
        headers=headers,
        data=data,
    )
    response = json.loads(req.text)

    try:
        secret = base64.b32encode(response["response"]["hotp_secret"].encode())
    except KeyError:
        _logger.warning("Failed to get secret")
        return False

    with open(DUO_KEYS_FILE, "w") as file:
        json.dump({"t": secret.decode(), "c": 0}, file)

    _logger.info("Duo keys generated")

    return True


def check_setup(settings):
    if not os.path.exists(DUO_KEYS_FILE):
        _logger.warning("Cannot find duo keys, initialising setup")

        return generate_duo_keys(settings)

    return True


if __name__ == "__main__":
    import settings_handler

    logging.basicConfig(level=logging.INFO)

    _settings = settingzer.Settings()
    # user will still have to fill in reject settings only leaving this in for the sake of exporting the secret

    check_setup(_settings)

    option = input(
        "[0] generate hotp code\r\n"
        "[1] export secret (might want to run in console output is quite large)\r\n"
        "?> "
    )

    if option == "0":
        print(generate_code())

    elif option == "1":
        export_code(_settings)

    else:
        print("Invalid option")
