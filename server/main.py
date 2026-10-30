import dbus
import dbus.mainloop.glib

from gi.repository import GLib

from server.dbus_service import LolacapService


def main():

    # Initialize the GLib main loop for D-Bus
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    # Connect to the session bus
    bus = dbus.SessionBus()

    # Register the Lolacap service
    service = LolacapService(bus)

    print("Lolacap D-Bus server is running...", flush=True)

    # Keep the server alive
    loop = GLib.MainLoop()
    loop.run()


if __name__ == "__main__":
    main()