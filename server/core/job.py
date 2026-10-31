
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


JobStatus = Literal[
    "queued",
    "running",
    "done",
    "failed",
    "cancelled",
    "interrupted",
]


@dataclass
class Job:
    id: str
    source: str
    language: str
    softcoded: bool

    status: JobStatus = "queued"
    progress: int = 0
    output_path: str = ""
    error: str = ""

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self):
        if not self.id:
            raise ValueError("Job ID cannot be empty")

        if not self.source:
            raise ValueError("Job source cannot be empty")

        if self.language not in ("fon", "yo"):
            raise ValueError(f"Unsupported language: {self.language}")

        if not 0 <= self.progress <= 100:
            raise ValueError("Progress must be between 0 and 100")
