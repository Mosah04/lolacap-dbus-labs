
import sqlite3
from pathlib import Path


class Database:
    def __init__(self, database_path: str):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)

        connection.row_factory = sqlite3.Row

        connection.execute("PRAGMA foreign_keys = ON")

        return connection
