import dbus
import dbus.service

from server.job_manager import JobManager


BUS_NAME = "org.lolacap.Service"
OBJECT_PATH = "/org/lolacap/Service"
INTERFACE = "org.lolacap.Service1"


class LolacapService(dbus.service.Object):

    def __init__(self, bus):
        self.job_manager = JobManager()

        self.bus_name = dbus.service.BusName(
            BUS_NAME,
            bus=bus
        )

        super().__init__(self.bus_name, OBJECT_PATH)

    @dbus.service.method(
        INTERFACE,
        in_signature="",
        out_signature="a{ss}"
    )
    def ListLanguages(self):
        return {
            "fon": "Fon",
            "yo": "Yoruba"
        }

    @dbus.service.method(
        INTERFACE,
        in_signature="ssb",
        out_signature="s"
    )
    def StartJob(self, video_path, language, softcoded):

        if language not in ("fon", "yo"):
            raise dbus.exceptions.DBusException(
                "Unsupported language"
            )

        job_id = self.job_manager.create_job(
            video_path,
            language,
            softcoded
        )

        return job_id

    @dbus.service.method(
        INTERFACE,
        in_signature="s",
        out_signature="suss"
    )
    def GetJob(self, job_id):

        try:
            job = self.job_manager.get_job(job_id)

        except KeyError:
            raise dbus.exceptions.DBusException(
                "Job not found"
            )

        return (
            job["state"],
            job["percentage"],
            job["output"],
            job["error"]
        )