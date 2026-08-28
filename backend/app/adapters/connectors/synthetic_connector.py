"""
synthetic_connector.py

File-based connectors that read the synthetic/test-fixture datasets from
/data/synthetic/. Each expects a specific JSON shape and normalizes it into
a NormalizedDocument. Per the finalized MVP scope, these are used for
testing, regression, and evaluation ONLY — the live demo path uses the
real GitHub/Notion/Slack connectors in this same package.

Expected JSON shape per file, e.g. data/synthetic/refund_handling/emails/e001.json:
{
  "author": "jane.doe@company.com",
  "author_role": "Manager",     <- optional; real/messy data should omit
                                    this and let authority_inference
                                    (core/domain/authority_scoring.py)
                                    infer it instead
  "timestamp": "2026-03-14T09:00:00",
  "content": "the actual email/chat/ticket text",
  "thread_context": "optional, e.g. thread subject or channel name"
}

Policy docs are plain .md/.txt files instead of JSON; author/role/date
are inferred from a small header convention (see PolicyDocConnector).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.adapters.connectors.base import SourceConnector
from app.core.domain.entities import NormalizedDocument, SourceType


class _JSONFileConnector(SourceConnector):
    """Shared logic for email/chat/ticket connectors, which all read
    one JSON file per document from a folder."""

    source_type: SourceType

    def extract(self, since: Optional[datetime] = None) -> list[NormalizedDocument]:
        # `since` is accepted for interface compatibility but ignored here —
        # synthetic fixtures are small and always read in full.
        documents = []
        if not self.source_dir.exists():
            return documents

        for file_path in sorted(self.source_dir.glob("*.json")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content_str = f.read().strip()
                    if not content_str:
                        continue
                    raw = json.loads(content_str)

                documents.append(
                    NormalizedDocument(
                        source_id=file_path.stem,
                        source_type=self.source_type,
                        content=raw["content"],
                        author=raw.get("author", "unknown"),
                        author_role=raw.get("author_role", "Unknown"),
                        timestamp=raw["timestamp"],
                        thread_context=raw.get("thread_context"),
                    )
                )
            except Exception as e:
                print(f"[synthetic_connector] Skipping invalid file {file_path}: {e}")
                continue
        return documents


class EmailConnector(_JSONFileConnector):
    source_type = SourceType.EMAIL


class ChatConnector(_JSONFileConnector):
    source_type = SourceType.CHAT


class TicketConnector(_JSONFileConnector):
    source_type = SourceType.TICKET


class PolicyDocConnector(SourceConnector):
    """
    Policy docs are plain markdown/text files. Metadata is read from a
    simple front-matter-style header at the top of the file:

        ---
        author: Support Policy Team
        author_role: Director
        timestamp: 2026-01-01T00:00:00
        ---
        (rest of the document is the policy content)
    """

    def extract(self, since: Optional[datetime] = None) -> list[NormalizedDocument]:
        documents = []
        if not self.source_dir.exists():
            return documents

        for file_path in sorted(self.source_dir.glob("*.md")) + sorted(self.source_dir.glob("*.txt")):
            text = file_path.read_text(encoding="utf-8")
            metadata, content = self._split_front_matter(text)

            documents.append(
                NormalizedDocument(
                    source_id=file_path.stem,
                    source_type=SourceType.POLICY_DOC,
                    content=content.strip(),
                    author=metadata.get("author", "unknown"),
                    author_role=metadata.get("author_role", "Unknown"),
                    timestamp=metadata.get("timestamp", "2020-01-01T00:00:00"),
                    thread_context=None,
                )
            )
        return documents

    @staticmethod
    def _split_front_matter(text: str) -> tuple[dict, str]:
        if not text.startswith("---"):
            return {}, text

        parts = text.split("---", 2)
        if len(parts) < 3:
            return {}, text

        header_block, body = parts[1], parts[2]
        metadata = {}
        for line in header_block.strip().splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
        return metadata, body


def load_all_sources(process_dir: Path) -> list[NormalizedDocument]:
    """
    Convenience function: given a process folder
    (e.g. data/synthetic/refund_handling), runs every connector and
    returns the combined, normalized document list. This is the single
    entry point extract_rules.py should call for synthetic/test data.
    """
    process_dir = Path(process_dir)
    connectors = [
        EmailConnector(process_dir / "emails"),
        ChatConnector(process_dir / "chats"),
        TicketConnector(process_dir / "tickets"),
        PolicyDocConnector(process_dir / "policy_docs"),
    ]
    all_docs: list[NormalizedDocument] = []
    for connector in connectors:
        all_docs.extend(connector.extract())
    return all_docs
