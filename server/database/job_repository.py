
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from server.core.job import Job


class JobRepository:
    def __init__(self, database):
        self.database = database

    def initialize(self):
        with closing(self.database.connect()) as connection:
            with connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS jobs (
                        id TEXT PRIMARY KEY,
                        source TEXT NOT NULL,
                        language TEXT NOT NULL,
                        softcoded INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        progress INTEGER NOT NULL DEFAULT 0,
                        output_path TEXT NOT NULL DEFAULT '',
                        error TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)

    def create(self, job: Job):
        with closing(self.database.connect()) as connection:
            with connection:
                connection.execute("""
                    INSERT INTO jobs (
                        id, source, language, softcoded,
                        status, progress, output_path, error,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.id,
                    job.source,
                    job.language,
                    int(job.softcoded),
                    job.status,
                    job.progress,
                    job.output_path,
                    job.error,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat()
                ))

    def update(self, job: Job):
        with closing(self.database.connect()) as connection:
            with connection:
                cursor = connection.execute("""
                    UPDATE jobs
                    SET status = ?,
                        progress = ?,
                        output_path = ?,
                        error = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (
                    job.status,
                    job.progress,
                    job.output_path,
                    job.error,
                    job.updated_at.isoformat(),
                    job.id
                ))

                if cursor.rowcount == 0:
                    raise KeyError(f"Job not found: {job.id}")

    def get(self, job_id: str) -> Job | None:
        with closing(self.database.connect()) as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE id = ?",
                (job_id,)
            ).fetchone()

        if row is None:
            return None

        return self._row_to_job(row)

    def list_all(self) -> list[Job]:
        with closing(self.database.connect()) as connection:
            rows = connection.execute("""
                SELECT * FROM jobs
                ORDER BY created_at DESC
            """).fetchall()

        return [self._row_to_job(row) for row in rows]

    def recover_interrupted(self):
        now = datetime.now(timezone.utc).isoformat()

        with closing(self.database.connect()) as connection:
            with connection:
                cursor = connection.execute("""
                    UPDATE jobs
                    SET status = 'interrupted',
                        updated_at = ?
                    WHERE status IN ('queued', 'running')
                """, (now,))

        return cursor.rowcount

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        return Job(
            id=row["id"],
            source=row["source"],
            language=row["language"],
            softcoded=bool(row["softcoded"]),
            status=row["status"],
            progress=row["progress"],
            output_path=row["output_path"],
            error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )
