
import tempfile
import time
import unittest

from pathlib import Path

from server.core.job import Job
from server.database.connection import Database
from server.database.job_repository import JobRepository
from server.job_manager import JobManager


class ImmediateBackend:

    def process(
        self,
        video_path,
        language,
        softcoded,
        progress_callback=None,
        cancel_event=None
    ):
        if progress_callback:
            progress_callback(50)

        if cancel_event and cancel_event.is_set():
            raise InterruptedError("Job cancelled")

        return "result.srt"


class TestJobManagerPersistence(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        database_path = Path(self.temp_dir.name) / "lolacap.db"

        self.database = Database(str(database_path))
        self.repository = JobRepository(self.database)

        self.manager = JobManager(
            backend=ImmediateBackend(),
            repository=self.repository
        )

    def tearDown(self):
        self.manager.close()
        self.temp_dir.cleanup()

    def wait_until_finished(self, job_id, timeout=3):
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            job = self.manager.get_job(job_id)

            if job["state"] in ("done", "failed", "cancelled"):
                return job

            time.sleep(0.01)

        self.fail("Job did not finish in time")

    def test_job_is_persisted_after_creation(self):
        job_id = self.manager.create_job(
            "video.mp4",
            "fon",
            False
        )

        persisted_job = self.repository.get(job_id)

        self.assertIsNotNone(persisted_job)
        self.assertEqual(persisted_job.id, job_id)

    def test_job_result_is_persisted(self):
        job_id = self.manager.create_job(
            "video.mp4",
            "fon",
            False
        )

        result = self.wait_until_finished(job_id)

        self.assertEqual(result["state"], "done")
        self.assertEqual(result["percentage"], 100)

        persisted_job = self.repository.get(job_id)

        self.assertEqual(persisted_job.status, "done")
        self.assertEqual(persisted_job.progress, 100)
        self.assertEqual(persisted_job.output_path, "result.srt")

    def test_completed_job_is_restored_after_restart(self):
        job_id = self.manager.create_job(
            "video.mp4",
            "fon",
            False
        )

        self.wait_until_finished(job_id)

        self.manager.close()

        new_manager = JobManager(
            backend=ImmediateBackend(),
            repository=self.repository
        )

        try:
            restored_job = new_manager.get_job(job_id)

            self.assertEqual(restored_job["state"], "done")
            self.assertEqual(restored_job["percentage"], 100)
            self.assertEqual(restored_job["output"], "result.srt")

        finally:
            new_manager.close()

    def test_queued_and_running_jobs_are_recovered(self):
        queued_job = Job(
            id="queued-job",
            source="queued.mp4",
            language="fon",
            softcoded=False
        )

        running_job = Job(
            id="running-job",
            source="running.mp4",
            language="yo",
            softcoded=True,
            status="running",
            progress=40
        )

        self.repository.create(queued_job)
        self.repository.create(running_job)

        recovered_manager = JobManager(
            backend=ImmediateBackend(),
            repository=self.repository
        )

        try:
            self.assertEqual(
                recovered_manager.get_job("queued-job")["state"],
                "interrupted"
            )

            self.assertEqual(
                recovered_manager.get_job("running-job")["state"],
                "interrupted"
            )

        finally:
            recovered_manager.close()


if __name__ == "__main__":
    unittest.main()
