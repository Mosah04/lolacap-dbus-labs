
import time
import dbus


BUS_NAME = "org.lolacap.Service"
OBJECT_PATH = "/org/lolacap/Service"
INTERFACE = "org.lolacap.Service1"


def main():

    # Connect to the session bus
    bus = dbus.SessionBus()

    # Get the remote D-Bus object
    remote_object = bus.get_object(
        BUS_NAME,
        OBJECT_PATH
    )

    # Access the Lolacap interface
    service = dbus.Interface(
        remote_object,
        dbus_interface=INTERFACE
    )

    # 1. Get available languages
    languages = service.ListLanguages()

    print("Available languages:")
    for code, name in languages.items():
        print(f"  {code}: {name}")

    # 2. Start a new job
    try:
        job_id = service.StartJob(
            "video.mp4",
            "english",
            False
        )

    except dbus.exceptions.DBusException as error:
        print("Could not start job:", error.get_dbus_message())
        return

    print("\nJob started!")
    print("Job ID:", job_id)

    # 3. Monitor the job
    while True:

        state, percentage, output, error = service.GetJob(job_id)

        print(f"Status: {state} | Progress: {percentage}%")

        if state == "done":
            print("\nJob completed!")
            print("Output:", output)
            break

        if state == "failed":
            print("\nJob failed!")
            print("Error:", error)
            break

        time.sleep(1)


if __name__ == "__main__":
    main()
