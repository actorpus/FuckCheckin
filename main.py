import time
import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, StaleElementReferenceException
from selenium.webdriver.firefox.options import Options
import json
import os
import duo



KEYSFILE = "settings_DONOTSHARE.json"

with open("offsets.json") as file:
    settings = json.load(file)

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


if not os.path.exists("usersettings.json"):
    print("This application can either be run in manual authorisation mode or automatic authorisation mode\r\n"
          "Automatic authorisation mode will locally store a generator that can bypass the duo authentication\r\n"
          "This is optional, manual authorisation will send duo push notifications every time the application\r\n"
          "\tis run\r\n")

    option = input("[0] Manual authorisation\r\n[1] Automatic authorisation\r\n\t?> ")

    if option == "1":
        duo.check_setup()

    with open("usersettings.json", "w") as file:
        json.dump({
            "authentication": option
        }, file)

    AUTHMODE = bool(int(option))

else:
    with open("usersettings.json") as file:
        AUTHMODE = bool(int(json.load(file)["authentication"]))


INST_CODE = settings['reject']['inst']
COURSE_CODE = settings['reject']['course']
YEAR = settings['reject']['year']

print("Getting codes fron reject")
modules = requests.get(f"https://rejectdopamine.com/api/app/find/{INST_CODE}/{YEAR}/{COURSE_CODE}/md").json()["modules"]
modules = [module["module_code"] for module in modules]

codes = []

for module in modules:
    r = requests.get(f"https://rejectdopamine.com/api/app/codes/{INST_CODE}/{COURSE_CODE}/{YEAR}/{module}").json()
    for _ in r: codes.append(_)

codes.sort(key=lambda x: x["count"])

print("Found codes, Loading webbrowser")

options = Options()
options.add_argument("-headless")
driver = webdriver.Firefox(options=options)


driver.get("https://checkin.york.ac.uk/")

while not driver.execute_script("return document.readyState") == "complete": time.sleep(0.2)

if driver.current_url.startswith("https://shib.york.ac.uk"):
    # Log in
    print("Attempting log in")
    username = driver.find_element("xpath", settings['navigation']['username'])
    username.send_keys(USERNAME)

    password = driver.find_element("xpath", settings['navigation']['password'])
    password.send_keys(PASSWORD)

    log_in = driver.find_element("xpath", settings['navigation']['log_in'])
    log_in.click()

    while not driver.execute_script("return document.readyState") == "complete": time.sleep(0.2)
    time.sleep(1)

    duo_frame = driver.find_element("xpath", settings['navigation']['duo_frame'])
    driver.switch_to.frame(duo_frame)

    while not driver.execute_script("return document.readyState") == "complete": time.sleep(0.2)
    time.sleep(1)


    if AUTHMODE:
        for _ in range(50):
            try:
                push_button = driver.find_element("xpath", settings['navigation']['duo_passcode'])
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

        passcode = driver.find_element("xpath", settings['navigation']['duo_passcode_entry'])
        passcode.send_keys(duo.generate_code())

        push_button = driver.find_element("xpath", settings['navigation']['duo_passcode'])
        push_button.click()

    else:
        for _ in range(50):
            try:
                push_button = driver.find_element("xpath", settings['navigation']['duo_request'])
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

        print("Please authorise the login on your phone")

    driver.switch_to.default_content()

    while not driver.current_url.startswith("https://checkin.york.ac.uk"): time.sleep(0.2)

print("Log in successful, trying codes")

while not driver.execute_script("return document.readyState") == "complete": time.sleep(0.2)

try:
    present_button = driver.find_element("xpath", settings['navigation']['present_button'])
    present_button.click()
except ElementNotInteractableException:
    print("you should never see this line of text")

except NoSuchElementException:
    print("No classes (not signed in already) could be found")
    exit()

for code in codes:
    while not driver.execute_script("return document.readyState") == "complete": time.sleep(0.2)
    time.sleep(2)

    code_feild = driver.find_element("xpath", settings['navigation']['code_feild'])
    code_feild.send_keys(code["checkinCode"])

    time.sleep(2)

    submit_button = driver.find_element("xpath", settings['navigation']['submit_button'])
    submit_button.click()

    time.sleep(5)

    try:
        present_button = driver.find_element("xpath", settings['navigation']['present_button'])
        present_button.click()
    except ElementNotInteractableException:
        break

    except NoSuchElementException:
        print("No classes (not signed in already) could be found")
        exit()

else:
    print("Entering code failed")
    exit()

print("Successfully signed in", code)
