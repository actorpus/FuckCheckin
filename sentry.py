import rejector
import json
from datetime import datetime, timezone
import time
import main
import winsound  # Windows only


try:
    print("This script uses the windows sounds methods, please enable and max the volume of system sounds.\r\n"
          "It will activate an alarm if it cannot sign in at the last 15 minutes of a session\r\n"
          "Playing a test sound now... ", end="")

    time.sleep(4)

    for _ in range(3):
        winsound.Beep(1000, 750)
        winsound.Beep(1500, 750)

    print("Test sound played, If you did not hear it, please enable system sounds and try again")
    time.sleep(2)


    print("Loading main to test for hangups...")
    main.main()

    print("Hopefully no hangups next time")

    with open("usersettings.json") as file:
        settings = json.load(file)
        INST, YEAR, COURSE = settings["reject"]

    while True:
        print("Checking for active sessions")

        sessions = rejector.getCodes(INST, COURSE, YEAR, return_events=True)

        if not sessions:
            print("No sessions found")

            print("Waiting 15 mins... ", end="")
            time.sleep(60 * 15)
            print("Waited")


        for session in sessions:
            startcode = datetime.strptime(f"{session['startDate']} {session['startTime']}", "%a %b %d %Y %H:%M").timestamp()
            endcode = datetime.strptime(f"{session['startDate']} {session['endTime']}", "%a %b %d %Y %H:%M").timestamp()

            if startcode < time.time() < endcode:
                print("Currently active session detected")

                break

        else:
            print("No active sessions found")

            print("Waiting 15 mins... ", end="")
            time.sleep(60 * 15)
            print("Waited")

            continue

        print("Launching main script")
        result = main.main()

        if result:
            print("Main script signed in successfully")

            print("Waiting 15 mins... ", end="")
            time.sleep(60 * 15)
            print("Waited")

        else:
            print("Main script failed to sign in")

            if endcode - time.time() < 60 * 15:
                print("Session ending in less than 10 mins, Panicking...")

                for _ in range(60 * 2):
                    winsound.Beep(1000, 750)
                    winsound.Beep(1500, 750)

            print("Waiting 5 mins... ", end="")
            time.sleep(60 * 5)
            print("Waited")

except Exception as e:
    print(f"An error occurred: {e}")
    for _ in range(60 * 2):
        winsound.Beep(1000, 750)
        winsound.Beep(1500, 750)