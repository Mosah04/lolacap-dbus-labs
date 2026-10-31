
import unittest
from unittest.mock import Mock

from server.dbus_service import LolacapService


class TestDBusService(unittest.TestCase):

    def setUp(self):
        # Avoid creating a real D-Bus connection.
        self.service = LolacapService.__new__(LolacapService)
        self.service.job_manager = Mock()

    def test_cancel_job(self):
        self.service.job_manager.cancel_job.return_value = True

        result = self.service.CancelJob("job-001")

        self.assertTrue(result)
        self.service.job_manager.cancel_job.assert_called_once_with(
            "job-001"
        )

    def test_cancel_completed_job(self):
        self.service.job_manager.cancel_job.return_value = False

        result = self.service.CancelJob("job-001")

        self.assertFalse(result)

    def test_cancel_unknown_job(self):
        self.service.job_manager.cancel_job.side_effect = KeyError(
            "Job not found"
        )

        with self.assertRaises(Exception):
            self.service.CancelJob("unknown-id")

    def test_list_jobs(self):
        self.service.job_manager.list_jobs.return_value = [
            {
                "id": "job-001",
                "state": "done",
                "percentage": 100,
                "output": "output.srt",
                "error": ""
            },
            {
                "id": "job-002",
                "state": "running",
                "percentage": 50,
                "output": "",
                "error": ""
            }
        ]

        result = self.service.ListJobs()

        self.assertEqual(result, [
            ("job-001", "done", 100, "output.srt", ""),
            ("job-002", "running", 50, "", "")
        ])


if __name__ == "__main__":
    unittest.main()
