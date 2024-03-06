import logging
import os
import json
import reject_api

_logger = logging.getLogger("SETTINGS")
SETTINGS_FILE = "settings.DONOTSHARE.json"
VERSION = "2.0"


class Settings:
    def __init__(self):
        self._username = None
        self._password = None

        self._reject_institution = None
        self._reject_year = None
        self._reject_course = None

        self._load_settings()

    def _load_settings(self):
        if not os.path.exists(SETTINGS_FILE):
            _logger.warning("Settings file not found, initializing setup")
            self._setup()

        with open(SETTINGS_FILE) as file:
            settings = json.load(file)

        version = settings.get("version", "0.0")

        if version != VERSION:
            _logger.warning(
                "Version mismatch, deleting user settings file, rerunning setup"
            )
            os.remove(SETTINGS_FILE)
            self._load_settings()

        self._username = settings["username"]
        self._password = settings["password"]

        self._reject_institution = settings["reject_institution"]
        self._reject_year = settings["reject_year"]
        self._reject_course = settings["reject_course"]

        _logger.info("Settings loaded")

    def _setup(self):
        _logger.info("Starting setup")

        username = input("Username ?> ")
        password = input("Password ?> ")
        institution, year, course = rejector.setup()

        with open(SETTINGS_FILE, "w") as file:
            json.dump(
                {
                    "username": username,
                    "password": password,
                    "reject_institution": institution,
                    "reject_year": year,
                    "reject_course": course,
                    "version": VERSION,
                },
                file,
            )

        _logger.info(
            f"Setup complete, settings saved to settings.DONOTSHARE.json version {VERSION}"
        )

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password

    @property
    def reject_institution(self):
        return self._reject_institution

    @property
    def reject_year(self):
        return self._reject_year

    @property
    def reject_course(self):
        return self._reject_course


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    settings = Settings()

    print(settings.username)
