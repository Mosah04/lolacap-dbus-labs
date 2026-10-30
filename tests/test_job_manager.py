import time
from server.job_manager import JobManager

manager = JobManager()

job_id = manager.create_job("video.mp4", "fon", False)

print("\nJob ID:", job_id)

while True:
    job = manager.get_job(job_id)
    print("Status:", job)

    if job["state"] in ("done", "failed"):
        break

    time.sleep(1)