import base64
import os
import sys
import pyqrcode
import pyotp
import requests
from Crypto.PublicKey import RSA
import json

SETTINGSFILE = "duosession_DONOTSHARE.json"


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



if not os.path.exists(SETTINGSFILE):
    print("[DUO] Cannot find configuration, initialising setup")
    print("[DUO] Navigate to https://duo.york.ac.uk/manage \r\n\t+Add another divice\r\n\t"
          "Tablet\r\n\tAndroid\r\n\tI Have Duo Mobile Installed\r\n\tEmail me an...")

    email = input("[DUO] Enter the link sent your email ?> ")

    print("[DUO] This may take a seccond")

    host = email.split(".")[0].split("-")[1]
    host = f'api-{host}.duosecurity.com'

    code = email.rsplit("/", 1)[1]

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

if __name__ == '__main__':
    option = input("[0] generate hotp code\r\n[1] export secret (might want to run in console output is quite large)"
                   "\r\n?> ")

    if option == "0":
        print(generate_code())

    elif option == "1":
        export_code()