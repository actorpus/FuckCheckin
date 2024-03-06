import time
import requests
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementNotInteractableException,
    StaleElementReferenceException,
)
from selenium.webdriver.firefox.options import Options
import json
import os
import duo
import rejector


KEYSFILE = "settings_DONOTSHARE.json"
OFFSETFILE = "offsets.json"
USERSETTINGSFILE = "usersettings.json"
HEADERS = {"User-Agent": "FuckCheckin/1.1"}
FILESVERSION = "1.0"

def main():
    # probably should be split up a bit

    with open(OFFSETFILE) as file:
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
            json.dump({"username": USERNAME, "password": PASSWORD}, file)


    if not os.path.exists(USERSETTINGSFILE):
        print(
            "This application can either be run in manual authorisation mode or automatic authorisation mode\r\n"
            "Automatic authorisation mode will locally store a generator that can bypass the duo authentication\r\n"
            "This is optional, manual authorisation will send duo push notifications every time the application\r\n"
            "\tis run\r\n"
        )

        auth_option = input(
            "[0] Manual authorisation\r\n[1] Automatic authorisation (recommended)\r\n\t?> "
        )

        print(
            "This application can either be ran headless or not (both the main app and the duo system)\r\n"
            "If not running headless you will be able to see the browser window and interact with it\r\n"
            "It is advices to only not run headless if you are having issues with the application\r\n"
        )

        head_option = input("[0] Headless (recommended)\r\n[1] Not headless\r\n\t?> ")
        #                                                      Head? Headed?

        reject_setup = rejector.setup()

        with open(USERSETTINGSFILE, "w") as file:
            json.dump(
                {
                    "authentication": auth_option,
                    "reject": reject_setup,
                    "show_window": head_option,
                    "version": FILESVERSION,
                },
                file,
            )

        AUTHMODE = bool(int(auth_option))
        HEADLESS = not bool(int(head_option))
        INST_CODE, YEAR, COURSE_CODE = reject_setup

    else:
        with open(USERSETTINGSFILE) as file:
            settings = json.load(file)

        version = settings.get("version", "0.0")

        if version != FILESVERSION:
            print(
                "Your settings file is out of date and has been removed, please re-run the application"
            )
            os.remove(USERSETTINGSFILE)
            return False

        AUTHMODE = bool(int(settings["authentication"]))
        INST_CODE, YEAR, COURSE_CODE = settings["reject"]
        HEADLESS = not bool(int(settings["show_window"]))


    if AUTHMODE:
        duo.check_setup()


    # Use reject's API to get codes
    codes = rejector.getCodes(INST_CODE, COURSE_CODE, YEAR)
    print(codes)
    if codes == []: return False

    options = Options()
    if HEADLESS:
        options.add_argument("-headless")
    driver = webdriver.Firefox(options=options)


    driver.get("https://checkin.york.ac.uk/")

    while not driver.execute_script("return document.readyState") == "complete":
        time.sleep(0.2)

    if driver.current_url.startswith("https://shib.york.ac.uk"):
        # Log in
        print("Attempting log in")
        username = driver.find_element("xpath", OFFSETS["username"])
        username.send_keys(USERNAME)

        password = driver.find_element("xpath", OFFSETS["password"])
        password.send_keys(PASSWORD)

        log_in = driver.find_element("xpath", OFFSETS["log_in"])
        log_in.click()

        while not driver.execute_script("return document.readyState") == "complete":
            time.sleep(0.2)
        time.sleep(1)

        duo_frame = driver.find_element("xpath", OFFSETS["duo_frame"])
        driver.switch_to.frame(duo_frame)

        while not driver.execute_script("return document.readyState") == "complete":
            time.sleep(0.2)
        time.sleep(1)

        if AUTHMODE:
            for _ in range(50):
                try:
                    push_button = driver.find_element("xpath", OFFSETS["duo_passcode"])
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
                return False

            passcode = driver.find_element("xpath", OFFSETS["duo_passcode_entry"])
            passcode.send_keys(duo.generate_code())

            push_button = driver.find_element("xpath", OFFSETS["duo_passcode"])
            push_button.click()

        else:
            for _ in range(50):
                try:
                    push_button = driver.find_element("xpath", OFFSETS["duo_request"])
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
                return False

            print("Please authorise the login on your phone")

        driver.switch_to.default_content()

        while not driver.current_url.startswith("https://checkin.york.ac.uk"):
            time.sleep(0.2)

    print("Log in successful, trying codes")

    while not driver.execute_script("return document.readyState") == "complete":
        time.sleep(0.2)

    token = driver.execute_script('return $(".dropdown-locale").data("csrf");')
    xsrf_token = driver.get_cookie("XSRF-TOKEN")["value"]
    prestostudent_session = driver.get_cookie("prestostudent_session")["value"]


    print(f"""
token = \"{token}\"
xsrf_token = \"{xsrf_token}\"
prestostudent_session = \"{prestostudent_session}\"
""")

    nodes = driver.find_elements("css selector", "section[data-activities-id]")
    events = []

    for node in nodes:
        events.append(node.get_attribute("data-activities-id"))

    if HEADLESS:
        # When not running in headless mode the browser will stay open to confirm the checkin
        driver.quit()

    print("Trying codes: ", end="")

    success = False

    for event in events:
        for code in codes:
            req = requests.post(
                f"https://checkin.york.ac.uk/api/selfregistration/{event}/present",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "Referer": "https://checkin.york.ac.uk/selfregistration",
                    "Cookie": f"XSRF-TOKEN={xsrf_token}; prestostudent_session={prestostudent_session}",
                },
                data={
                    "code": code,
                    "_token": token,
                },
            )

            print(f"{code} - {req.status_code}", end=" ")
            print(req.text, end=" ")

            if req.status_code == 422:
                print("O", end=", ")
                continue

            print("#")

            print(f"{code} - {req.status_code}")
            success = True

            break

        else:
            print("\nNo valid codes found (you might already be checked in)")
            continue

        break


    if not HEADLESS:
        driver.refresh()
        time.sleep(5)
        driver.quit()

    print("Done")


    return success

if __name__ == '__main__':
    main()
