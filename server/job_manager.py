import threading
import uuid

from server.backend.fake_backend import FakeBackend


class JobManager:

    def __init__(self):
        self.backend = FakeBackend()
        self.jobs = {}
        self.lock = threading.Lock()

    def create_job(self, video_path: str, language: str, softcoded: bool) -> str:
        job_id = str(uuid.uuid4())

        with self.lock:
            self.jobs[job_id] = {
                "state": "queued",
                "percentage": 0,
                "output": "",
                "error": ""
            }

        thread = threading.Thread(
            target=self._process_job,
            args=(job_id, video_path, language, softcoded),
            daemon=True
        )

        thread.start()

        return job_id

    def _process_job(self, job_id, video_path, language, softcoded):

        with self.lock:
            self.jobs[job_id]["state"] = "running"
            self.jobs[job_id]["percentage"] = 10

        try:
            output = self.backend.process(
                video_path,
                language,
                softcoded
            )

            with self.lock:
                self.jobs[job_id]["state"] = "done"
                self.jobs[job_id]["percentage"] = 100
                self.jobs[job_id]["output"] = output

        except Exception as error:
            with self.lock:
                self.jobs[job_id]["state"] = "failed"
                self.jobs[job_id]["error"] = str(error)

    def get_job(self, job_id: str) -> dict:

        with self.lock:
            if job_id not in self.jobs:
                raise KeyError(f"Job not found: {job_id}")

            return self.jobs[job_id].copy()