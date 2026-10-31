
import time
import threading
import unittest

from server.job_manager import JobManager


class TrackingBackend:

    def __init__(self):
        self.lock = threading.Lock()
        self.active_jobs = 0
        self.max_active_jobs = 0

    def process(
        self,
        video_path,
        language,
        softcoded,
        progress_callback=None,
        cancel_event=None
    ):

        with self.lock:
            self.active_jobs += 1
            self.max_active_jobs = max(
                self.max_active_jobs,
                self.active_jobs
            )

        try:
            if progress_callback:
                progress_callback(25)

            time.sleep(0.1)

            if progress_callback:
                progress_callback(60)

            time.sleep(0.1)

            if progress_callback:
                progress_callback(90)

            return f"{video_path}.srt"

        finally:
            with self.lock:
                self.active_jobs -= 1



class TestJobManager(unittest.TestCase):

    def setUp(self):
        self.backend = TrackingBackend()
        self.manager = JobManager(backend=self.backend)

    def tearDown(self):
        self.manager.close()


    def wait_until_finished(
        self,
        job_ids,
        manager=None,
        timeout=5
    ):
        manager = manager or self.manager

        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            jobs = [
                manager.get_job(job_id)
                for job_id in job_ids
            ]

            if all(
                job["state"] in ("done", "failed", "cancelled")
                for job in jobs
            ):
                return jobs

            time.sleep(0.02)

        self.fail("Jobs did not finish in time")


    def test_job_completion(self):

        job_id = self.manager.create_job(
            "video.mp4",
            "fon",
            False
        )

        job = self.wait_until_finished([job_id])[0]

        self.assertEqual(job["state"], "done")
        self.assertEqual(job["percentage"], 100)
        self.assertEqual(job["output"], "video.mp4.srt")

    def test_jobs_are_processed_sequentially(self):

        job_ids = [
            self.manager.create_job(
                f"video_{i}.mp4",
                "fon",
                False
            )
            for i in range(5)
        ]

        self.wait_until_finished(job_ids)

        self.assertEqual(
            self.backend.max_active_jobs,
            1
        )

    def test_get_unknown_job(self):

        with self.assertRaises(KeyError):
            self.manager.get_job("unknown-id")

    def test_invalid_language(self):

        with self.assertRaises(ValueError):
            self.manager.create_job(
                "video.mp4",
                "english",
                False
            )

    def test_progress_reaches_100(self):

        job_id = self.manager.create_job(
            "video.mp4",
            "fon",
            False
        )

        job = self.wait_until_finished([job_id])[0]

        self.assertEqual(job["percentage"], 100)


    def test_progress_cannot_decrease(self):

        job_id = self.manager.create_job(
            "video.mp4",
            "fon",
            False
        )

        # Wait until the worker starts processing.
        deadline = time.monotonic() + 2

        while time.monotonic() < deadline:
            job = self.manager.get_job(job_id)

            if job["state"] == "running":
                break

            time.sleep(0.01)

        self.assertEqual(job["state"], "running")

        with self.assertRaises(ValueError):
            self.manager._update_progress(job_id, 5)

    def test_cancel_queued_job(self):

        backend = BlockingBackend()
        manager = JobManager(backend=backend)

        try:
            first_id = manager.create_job(
                "first.mp4", "fon", False
            )

            self.assertTrue(backend.started.wait(timeout=2))

            second_id = manager.create_job(
                "second.mp4", "fon", False
            )

            self.assertTrue(manager.cancel_job(second_id))

            backend.release.set()

            jobs = self.wait_until_finished(
                [first_id, second_id],
                manager=manager
            )

            self.assertEqual(jobs[0]["state"], "done")
            self.assertEqual(jobs[1]["state"], "cancelled")
            self.assertEqual(backend.processed, ["first.mp4"])

        finally:
            backend.release.set()
            manager.close()


    def test_cancel_running_job(self):

        backend = CancelAwareBackend()
        manager = JobManager(backend=backend)

        try:
            job_id = manager.create_job(
                "video.mp4", "fon", False
            )

            self.assertTrue(backend.started.wait(timeout=2))

            self.assertTrue(manager.cancel_job(job_id))

            job = self.wait_until_finished(
                [job_id],
                manager=manager
            )[0]

            self.assertEqual(job["state"], "cancelled")

        finally:
            manager.close()

    def test_close_cancels_running_and_queued_jobs(self):

        backend = CancelAwareBackend()
        manager = JobManager(backend=backend)

        first_id = manager.create_job(
            "first.mp4", "fon", False
        )

        self.assertTrue(backend.started.wait(timeout=2))

        second_id = manager.create_job(
            "second.mp4", "fon", False
        )

        # Close should cancel both jobs and stop the worker.
        stopped = manager.close(timeout=2)

        self.assertTrue(stopped)

        self.assertEqual(
            manager.get_job(first_id)["state"],
            "cancelled"
        )

        self.assertEqual(
            manager.get_job(second_id)["state"],
            "cancelled"
        )

        self.assertFalse(manager.worker.is_alive())

        # A closed manager must reject new jobs.
        with self.assertRaises(RuntimeError):
            manager.create_job(
                "third.mp4", "fon", False
            )

    def test_list_jobs(self):
        first_id = self.manager.create_job(
            "first.mp4", "fon", False
        )
        second_id = self.manager.create_job(
            "second.mp4", "yo", True
        )

        jobs = self.manager.list_jobs()

        self.assertEqual(len(jobs), 2)

        job_ids = {job["id"] for job in jobs}

        self.assertEqual(job_ids, {first_id, second_id})
    
    def test_job_updates_are_notified(self):
        events = []

        manager = JobManager(
            on_job_updated=lambda event: events.append(event)
        )

        try:
            job_id = manager.create_job("video.mp4", "fon", False)

            # Attendre que le traitement se termine.
            manager.job_queue.join()

            states = [event["state"] for event in events]

            self.assertIn("running", states)
            self.assertIn("done", states)

            self.assertEqual(events[-1]["percentage"], 100)

        finally:
            manager.close()


    def test_queued_cancellation_is_notified(self):
        events = []
        manager = JobManager(
            on_job_updated=lambda event: events.append(event)
        )

        try:
            job_id = manager.create_job("video.mp4", "fon", False)

            # Ce test nécessite que le worker soit occupé par une autre tâche
            # pour garantir que la tâche à annuler reste en attente.
            manager.cancel_job(job_id)

            cancelled_events = [
                event for event in events
                if event["id"] == job_id
                and event["state"] == "cancelled"
            ]

            self.assertEqual(len(cancelled_events), 1)

        finally:
            manager.close()



class BlockingBackend:

    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.processed = []

    def process(
        self,
        video_path,
        language,
        softcoded,
        progress_callback=None,
        cancel_event=None
    ):
        self.started.set()
        self.release.wait(timeout=3)

        self.processed.append(video_path)
        return f"{video_path}.srt"


class CancelAwareBackend:

    def __init__(self):
        self.started = threading.Event()

    def process(
        self,
        video_path,
        language,
        softcoded,
        progress_callback=None,
        cancel_event=None
    ):
        self.started.set()

        while not cancel_event.is_set():
            cancel_event.wait(timeout=0.02)

        raise InterruptedError("Job cancelled")




if __name__ == "__main__":
    unittest.main()
