import base64
import os
import sys
import pyqrcode
import pyotp
import requests
from Crypto.PublicKey import RSA
import json
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, StaleElementReferenceException
from selenium.webdriver.firefox.options import Options
import time
from pyzbar.pyzbar import decode
from PIL import Image

SETTINGSFILE = "duosession_DONOTSHARE.json"
KEYSFILE = "settings_DONOTSHARE.json"


def generate_code():
    with open(SETTINGSFILE, "r") as file:
        settings = json.load(file)

    secret = settings['t']
    count = settings['c']

    hotp = pyotp.HOTP(secret)
    code = hotp.at(count)

    print(f"[DUO] Code generation C{count}c{code}")

    settings['c'] += 1

    with open(SETTINGSFILE, "w") as j:
        json.dump(settings, j)

    return code


def export_code():
    with open(SETTINGSFILE, "r") as file:
        settings = json.load(file)

    qr = pyqrcode.create(
        f'otpauth://hotp/DUOKEY?secret={settings["t"].strip("=")}&issuer=actorpus&counter={settings["c"]}'
    )
    print(qr.terminal(quiet_zone=4))


def _duo_auth(host, code):
    url = f'https://{host}/push/v2/activation/{code}?customer_protocol=1'
    headers = {
        'User-Agent': 'okhttp/2.7.5'
    }
    data = {  # thanks to https://github.com/revalo/duo-bypass/commit/3dd0cf08bed7e7f5fbafa75b55320372528062d1
        'pkpush': 'rsa-sha512',
        'pubkey': RSA.generate(2048).public_key().export_key("PEM").decode(),
        'jailbroken': 'false',
        'architecture': 'arm64',
        'region': 'US',
        'app_id': 'com.duosecurity.duomobile',
        'full_disk_encryption': 'true',
        'passcode_status': 'true',
        'platform': 'Android',
        'app_version': '3.49.0',
        'app_build_number': '323001',
        'version': '11',
        'manufacturer': 'unknown',
        'language': 'en',
        'model': 'Pixel 3a',
        'security_patch_level': '2021-02-01'
    }

    r = requests.post(url, headers=headers, data=data)
    response = json.loads(r.text)

    try:
        secret = base64.b32encode(response['response']['hotp_secret'].encode())
    except KeyError:
        print(response)
        sys.exit(1)

    with open(SETTINGSFILE, "w") as file:
        json.dump({
            't': secret.decode(),
            'c': 0
        }, file)

    print("[DUO] Authentication sucsessfull")


def manual_setup():
    print("[DUO] Navigate to https://duo.york.ac.uk/manage \r\n\t+Add another divice\r\n\t"
          "Tablet\r\n\tAndroid\r\n\tI Have Duo Mobile Installed\r\n\tEmail me an...")

    email = input("[DUO] Enter the link sent your email ?> ")

    print("[DUO] This may take a seccond")

    host = email.split(".")[0].split("-")[1]
    host = f'api-{host}.duosecurity.com'

    code = email.rsplit("/", 1)[1]

    _duo_auth(host, code)


def automated_setup():
    with open("usersettings.json") as file:
        settings = json.load(file)
        HEADLESS = not bool(int(settings['show_window']))

    with open("offsets.json") as file:
        OFFSETS = json.load(file)

    if os.path.exists(KEYSFILE):
        with open(KEYSFILE, "r") as file:
            s = json.load(file)
            USERNAME = s["username"]
            PASSWORD = s["password"]


    else:
        print("Please enter username and password")
        USERNAME = input("username ?> ")
        PASSWORD = input("password ?> ")

        with open(KEYSFILE, "w") as file:
            json.dump({
                "username": USERNAME,
                "password": PASSWORD
            }, file)

    options = Options()
    if HEADLESS:
        options.add_argument("-headless")
    driver = webdriver.Firefox(options=options)

    driver.get("https://duo.york.ac.uk/manage")

    while not driver.execute_script("return document.readyState") == "complete": time.sleep(0.2)

    print("[DUO] Attempting to add duo device...")
    username = driver.find_element("xpath", OFFSETS['username'])
    username.send_keys(USERNAME)

    password = driver.find_element("xpath", OFFSETS['password'])
    password.send_keys(PASSWORD)

    log_in = driver.find_element("xpath", OFFSETS['log_in'])
    log_in.click()

    while not driver.current_url == "https://duo.york.ac.uk/manage": time.sleep(0.2)
    while not driver.execute_script("return document.readyState") == "complete": time.sleep(0.2)
    time.sleep(1)

    duo_frame = driver.find_element("xpath", OFFSETS['duo_frame'])

    driver.switch_to.frame(duo_frame)

    for _ in range(50):
        try:
            push_button = driver.find_element("xpath", OFFSETS['duo_push'])
            time.sleep(0.2)
            push_button.click()
            break
        except NoSuchElementException:
            time.sleep(0.2)
        except ElementNotInteractableException:
            time.sleep(0.2)
        except StaleElementReferenceException:
            time.sleep(0.2)
    else:
        print("Duo did not load / took to long to load")
        exit()

    print("[DUO] Please accept the duo push")

    for _ in range(50):
        try:
            t = driver.find_element("xpath", "//*[@id=\"header-title\"]")

            time.sleep(0.2)
            break
        except NoSuchElementException:
            time.sleep(0.2)

    else:
        print("Duo did not load / took to long to load")
        exit()

    add_device = driver.find_element("xpath", OFFSETS['duo_add_device'])
    add_device.click()

    while not driver.execute_script("return document.readyState") == "complete": time.sleep(0.2)

    add_tablet = driver.find_element("xpath", OFFSETS['duo_add_tablet'])
    add_tablet.click()

    add_continue = driver.find_element("xpath", OFFSETS['duo_add_continue'])
    add_continue.click()

    while not driver.execute_script("return document.readyState") == "complete": time.sleep(0.2)

    add_android = driver.find_element("xpath", OFFSETS['duo_add_android'])
    add_android.click()

    add_continue = driver.find_element("xpath", OFFSETS['duo_add_continue'])
    add_continue.click()

    while not driver.execute_script("return document.readyState") == "complete": time.sleep(0.2)

    installed = driver.find_element("xpath", OFFSETS['duo_installed'])
    installed.click()

    while not driver.execute_script("return document.readyState") == "complete": time.sleep(0.2)

    qr = driver.find_element("xpath", OFFSETS['duo_qr'])
    qr_url = qr.get_attribute("src")

    req = requests.get(qr_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"}, stream=True)
    req.raise_for_status()

    with open(".duoqr.tmp.png", "wb") as file:
        for chunk in req.iter_content(chunk_size=8192):
            file.write(chunk)

    img = Image.open(".duoqr.tmp.png")
    data = decode(img)
    data = data[0].data.decode()
    data = data.split("-")

    host = data[1] + "=" * (4 - len(data[1]) % 4)
    host = base64.b64decode(host).decode()
    host = host.split(".")[0].split("-")[1]
    host = f'api-{host}.duosecurity.com'
    code = data[0]

    _duo_auth(host, code)

    add_continue = driver.find_element("xpath", OFFSETS['duo_add_continue'])
    add_continue.click()

    while not driver.execute_script("return document.readyState") == "complete": time.sleep(0.2)
    time.sleep(1)

    driver.quit()
    os.remove(".duoqr.tmp.png")


def check_setup():
    if not os.path.exists(SETTINGSFILE):
        print("[DUO] Cannot find configuration, initialising setup")

        option = input("[0] Automated setup (recommended)\r\n"
                       "[1] Manual setup\r\n"
                       "?> ")

        if option == "0":
            automated_setup()
            print("[DUO] Setup complete, Duo authentication can now be skipped")

        elif option == "1":
            manual_setup()
            print("[DUO] Setup complete, Duo authentication can now be skipped")

        else:
            print("Invalid option")
            sys.exit(1)

if __name__ == '__main__':
    check_setup()

    option = input("[0] generate hotp code\r\n"
                   "[1] export secret (might want to run in console output is quite large)\r\n"
                   "?> ")

    if option == "0":
        print(generate_code())

    elif option == "1":
        export_code()

    else:
        print("Invalid option")
        sys.exit(1)
