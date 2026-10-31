
import queue
import threading
import uuid

from server.core.job import Job
from server.backend.fake_backend import FakeBackend
from server.database.job_repository import JobRepository

from datetime import datetime, timezone


class JobManager:

    def __init__(self, backend=None, repository=None):
        self.backend = backend or FakeBackend()
        self.repository = repository

        self.jobs = {}
        self.cancel_events = {}
        self.lock = threading.Lock()

        self.job_queue = queue.Queue()
        self.closed = False

        # Restore persisted jobs when a repository is provided.
        if self.repository is not None:
            self.repository.initialize()
            self.repository.recover_interrupted()

            for job in self.repository.list_all():
                self.jobs[job.id] = job
                self.cancel_events[job.id] = threading.Event()

        self.worker = threading.Thread(
            target=self._worker_loop,
            name="lolacap-worker",
            daemon=True
        )
        self.worker.start()

    def create_job(
        self,
        video_path: str,
        language: str,
        softcoded: bool
    ) -> str:

        job_id = str(uuid.uuid4())

        job = Job(
            id=job_id,
            source=video_path,
            language=language,
            softcoded=softcoded
        )

        with self.lock:
            if self.closed:
                raise RuntimeError("JobManager is closed")

            if self.repository:
                self.repository.create(job)

            self.jobs[job_id] = job
            self.cancel_events[job_id] = threading.Event()
            self.job_queue.put(job_id)

        return job_id

    def _save_job(self, job):
        if self.repository is not None:
            self.repository.update(job)

    def _worker_loop(self):

        while True:
            job_id = self.job_queue.get()

            try:
                if job_id is None:
                    return

                with self.lock:
                    job = self.jobs[job_id]

                    if job.status != "queued":
                        continue

                self._process_job(job_id)

            finally:
                self.job_queue.task_done()

    def _process_job(self, job_id: str):

        with self.lock:
            job = self.jobs[job_id]

            if job.status != "queued":
                return

            job.status = "running"
            job.progress = 0
            job.updated_at = datetime.now(timezone.utc)

            self._save_job(job)

        try:
            output = self.backend.process(
                job.source,
                job.language,
                job.softcoded,
                progress_callback=lambda progress: self._update_progress(
                    job_id,
                    progress
                ),
                cancel_event=self.cancel_events[job_id]
            )

            with self.lock:
                if self.cancel_events[job_id].is_set():
                    job.status = "cancelled"
                else:
                    job.status = "done"
                    job.progress = 100
                    job.output_path = output

                job.updated_at = datetime.now(timezone.utc)

                self._save_job(job)

        except InterruptedError:
            with self.lock:
                job.status = "cancelled"
                job.updated_at = datetime.now(timezone.utc)

                self._save_job(job)

        except Exception as error:
            with self.lock:
                job.status = "failed"
                job.error = str(error)
                job.updated_at = datetime.now(timezone.utc)

                self._save_job(job)

    def get_job(self, job_id: str) -> dict:

        with self.lock:
            if job_id not in self.jobs:
                raise KeyError(f"Job not found: {job_id}")

            job = self.jobs[job_id]

            # Keep the old API format for D-Bus compatibility.
            return {
                "state": job.status,
                "percentage": job.progress,
                "output": job.output_path,
                "error": job.error
            }

    def close(self, timeout: float = 5.0) -> bool:
        """
        Request a graceful shutdown.

        Returns True if the worker stopped within the timeout,
        False otherwise.
        """

        with self.lock:
            if not self.closed:
                self.closed = True

                for job_id, job in self.jobs.items():

                    if job.status == "queued":
                        self.cancel_events[job_id].set()
                        job.status = "cancelled"
                        job.updated_at = datetime.now(timezone.utc)
                        self._save_job(job)

                    elif job.status == "running":
                        self.cancel_events[job_id].set()

                # Stop the worker after it has skipped pending jobs.
                self.job_queue.put(None)

        self.worker.join(timeout=timeout)

        return not self.worker.is_alive()


    def _update_progress(self, job_id: str, progress: int):

        if not isinstance(progress, int) or isinstance(progress, bool):
            raise ValueError("Progress must be an integer")

        if not 0 <= progress <= 99:
            raise ValueError("Progress must be between 0 and 99")

        with self.lock:
            job = self.jobs[job_id]

            if job.status != "running":
                return

            if progress < job.progress:
                raise ValueError("Progress cannot decrease")

            job.progress = progress
            job.updated_at = datetime.now(timezone.utc)
            self._save_job(job)

    def cancel_job(self, job_id: str) -> bool:

        with self.lock:
            if job_id not in self.jobs:
                raise KeyError(f"Job not found: {job_id}")

            job = self.jobs[job_id]

            # A completed or already cancelled job cannot be cancelled again.
            if job.status in ("done", "failed", "cancelled", "interrupted"):
                return False

            # Signal the backend to stop if it is currently running.
            self.cancel_events[job_id].set()

            # A queued job can be cancelled immediately.
            if job.status == "queued":
                job.status = "cancelled"
                job.updated_at = datetime.now(timezone.utc)
                self._save_job(job)

            return True

