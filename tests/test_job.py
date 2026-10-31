
import unittest
from server.core.job import Job


class TestJob(unittest.TestCase):

    def test_job_creation(self):
        job = Job(
            id="test-123",
            source="video.mp4",
            language="fon",
            softcoded=False
        )

        self.assertEqual(job.id, "test-123")
        self.assertEqual(job.status, "queued")
        self.assertEqual(job.progress, 0)
        self.assertEqual(job.output_path, "")
        self.assertEqual(job.error, "")

    def test_invalid_language(self):
        with self.assertRaises(ValueError):
            Job(
                id="test-123",
                source="video.mp4",
                language="english",
                softcoded=False
            )

    def test_invalid_progress(self):
        with self.assertRaises(ValueError):
            Job(
                id="test-123",
                source="video.mp4",
                language="fon",
                softcoded=False,
                progress=150
            )

    def test_empty_source(self):
        with self.assertRaises(ValueError):
            Job(
                id="test-123",
                source="",
                language="fon",
                softcoded=False
            )


if __name__ == "__main__":
    unittest.main()
