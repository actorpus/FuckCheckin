import requests
from bs4 import BeautifulSoup
from pprint import pprint


# remember to remove the session before pushing
prestostudent_session = ""

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Accept": "text/html",
    "Accept-Encoding": "gzip, deflate, br",
    "Cookie": f"prestostudent_session={prestostudent_session}",
}

print("getting page")

req = requests.get(
    "https://checkin.york.ac.uk/selfregistration",
    headers=headers,
)

req.raise_for_status()

page = req.content.decode()

soup = BeautifulSoup(page, "html.parser")

title = soup.find("title").text

if title == "Please log in to continue...":
    print("Session expired, please log in again.")
    exit(1)

if title != "Check-In":
    print("Unexpected page title:", title)
    exit(1)

token = soup.find("meta", {"name": "csrf-token"})["content"]

print("token: ", token)
# Needed for submitting checkin requests

classes = soup.find_all("div", {"class": "text-block bs"})
events = []


for c in classes:
    event = {
        "time": c.find_all("div", {"class": "col-md-4"})[0].text.strip(),
        "activity": c.find_all("div", {"class": "col-md-4"})[1].text.strip(),
        "lecturer": c.find_all("div", {"class": "col-md-4"})[2].text.strip(),
        "space": c.find_all("div", {"class": "col-md-4"})[3].text.strip(),
    }

    options = c.find_all("div", {"class": "selfregistration_status"})

    for o in options:
        if o.get("class")[-1] == "hidden":
            continue

        event["status"] = o.find("div", {"class": "widget-simple-sm-bottom"}).text.strip()
        break

    else:
        event["status"] = "unknown"

    events.append(event)

print("events:")
pprint(events)