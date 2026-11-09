"""Store each appeal as an individual UTF-8 JSON document."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.models import StoredAppeal


class JsonAppealStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def save(self, appeal: StoredAppeal) -> None:
        """Publish a complete file atomically; propagate filesystem errors."""
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            # A temporary file in the same directory keeps the rename atomic.
            with NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.directory, suffix=".tmp", delete=False
            ) as stream:
                temporary_path = Path(stream.name)
                stream.write(appeal.model_dump_json(indent=2))
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            temporary_path.replace(self.directory / f"{appeal.id}.json")
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
