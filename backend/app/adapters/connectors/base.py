"""
base.py

Abstract interface every source connector must implement. Simulated
connectors (reading local files) and future live connectors (Slack API,
Gmail API, etc.) both implement this same interface, so extraction.py
never needs to know or care where a document came from.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.domain.entities import NormalizedDocument


class SourceConnector(ABC):
    """
    Every connector — synthetic or real (GitHub/Notion/Slack) — implements
    this exact interface. `since` supports incremental sync later without
    changing the signature; synthetic/file-based connectors can ignore it
    for now and just return everything.
    """

    def __init__(self, source_dir: Optional[Path] = None, config: Optional[dict] = None):
        self.source_dir = Path(source_dir) if source_dir else None
        self.config = config or {}

    @abstractmethod
    def extract(self, since: Optional[datetime] = None) -> list[NormalizedDocument]:
        """Return every document from this source, normalized.
        If `since` is given, only return documents newer than that
        timestamp (real connectors); synthetic/file connectors may ignore
        `since` and return everything every time."""
        raise NotImplementedError

    def stream(self, since: Optional[datetime] = None):
        """
        Default implementation just yields from extract(). Override this
        in a live connector (e.g. SlackConnector) to support paginated
        or incremental fetching without loading everything into memory.
        """
        yield from self.extract(since=since)
