"""Common interface every job source implements."""
from __future__ import annotations

from typing import List, Protocol

from app.models import JobPosting


class JobSource(Protocol):
    name: str

    def is_configured(self) -> bool:
        ...

    def search(self, query: str, location: str = "", limit: int = 20) -> List[JobPosting]:
        ...
