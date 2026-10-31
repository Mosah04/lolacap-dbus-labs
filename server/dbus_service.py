import os
import dbus
import dbus.service
from pathlib import Path
from gi.repository import GLib

from server.database.connection import Database
from server.database.job_repository import JobRepository

from server.job_manager import JobManager


BUS_NAME = "org.lolacap.Service"
OBJECT_PATH = "/org/lolacap/Service"
INTERFACE = "org.lolacap.Service1"


class LolacapService(dbus.service.Object):

    def __init__(self, bus):
        default_data_dir = Path.home() / ".local" / "share" / "lolacap"
        data_dir = Path(os.environ.get("LOLACAP_DATA_DIR", default_data_dir))

        database = Database(str(data_dir / "lolacap.db"))
        repository = JobRepository(database)

        self.bus_name = dbus.service.BusName(
            BUS_NAME,
            bus=bus
        )

        super().__init__(self.bus_name, OBJECT_PATH)

        self.job_manager = JobManager(
            repository=repository,
            on_job_updated=self._on_job_updated
        )

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

    @dbus.service.method(
        INTERFACE,
        in_signature="s",
        out_signature="b"
    )
    def CancelJob(self, job_id):

        try:
            return self.job_manager.cancel_job(job_id)

        except KeyError:
            raise dbus.exceptions.DBusException(
                "Job not found"
            )

    @dbus.service.method(
        INTERFACE,
        in_signature="",
        out_signature="a(ssuss)"
    )
    def ListJobs(self):
        jobs = self.job_manager.list_jobs()

        return [
            (
                job["id"],
                job["state"],
                job["percentage"],
                job["output"],
                job["error"]
            )
            for job in jobs
        ]

    @dbus.service.signal(
        INTERFACE,
        signature="ssuss"
    )
    def JobUpdated(self, job_id, state, percentage, output, error):
        pass
    
    def _on_job_updated(self, event):
        GLib.idle_add(self._emit_job_updated, event)


    def _emit_job_updated(self, event):
        self.JobUpdated(
            event["id"],
            event["state"],
            dbus.UInt32(event["percentage"]),
            event["output"],
            event["error"]
        )

        return GLib.SOURCE_REMOVE