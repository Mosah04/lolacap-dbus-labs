
import tempfile
import unittest

from pathlib import Path

from server.core.job import Job
from server.database.connection import Database
from server.database.job_repository import JobRepository


class TestJobRepository(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        database_path = Path(self.temp_dir.name) / "test.db"

        self.database = Database(str(database_path))
        self.repository = JobRepository(self.database)

        self.repository.initialize()

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_job(self, job_id="job-001"):
        return Job(
            id=job_id,
            source="video.mp4",
            language="fon",
            softcoded=False
        )

    def test_create_and_get_job(self):
        job = self.create_job()

        self.repository.create(job)

        retrieved = self.repository.get(job.id)

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, job.id)
        self.assertEqual(retrieved.source, job.source)
        self.assertEqual(retrieved.language, job.language)
        self.assertEqual(retrieved.softcoded, job.softcoded)
        self.assertEqual(retrieved.status, "queued")

    def test_get_unknown_job(self):
        result = self.repository.get("unknown-id")

        self.assertIsNone(result)

    def test_update_job(self):
        job = self.create_job()
        self.repository.create(job)

        job.status = "running"
        job.progress = 50

        self.repository.update(job)

        retrieved = self.repository.get(job.id)

        self.assertEqual(retrieved.status, "running")
        self.assertEqual(retrieved.progress, 50)

    def test_update_unknown_job(self):
        job = self.create_job("unknown-id")

        with self.assertRaises(KeyError):
            self.repository.update(job)

    def test_list_all_jobs(self):
        first = self.create_job("job-001")
        second = self.create_job("job-002")

        self.repository.create(first)
        self.repository.create(second)

        jobs = self.repository.list_all()

        self.assertEqual(len(jobs), 2)
        self.assertEqual(
            {job.id for job in jobs},
            {"job-001", "job-002"}
        )

    def test_recover_interrupted_jobs(self):
        queued = self.create_job("job-001")

        running = self.create_job("job-002")
        running.status = "running"
        running.progress = 40

        completed = self.create_job("job-003")
        completed.status = "done"
        completed.progress = 100

        self.repository.create(queued)
        self.repository.create(running)
        self.repository.create(completed)

        recovered_count = self.repository.recover_interrupted()

        self.assertEqual(recovered_count, 2)

        self.assertEqual(
            self.repository.get("job-001").status,
            "interrupted"
        )
        self.assertEqual(
            self.repository.get("job-002").status,
            "interrupted"
        )
        self.assertEqual(
            self.repository.get("job-003").status,
            "done"
        )

    def test_database_persistence(self):
        job = self.create_job()
        self.repository.create(job)

        # Simulate closing and reopening the database.
        new_database = Database(str(self.database.database_path))
        new_repository = JobRepository(new_database)

        retrieved = new_repository.get(job.id)

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, job.id)


if __name__ == "__main__":
    unittest.main()
