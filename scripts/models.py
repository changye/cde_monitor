from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class QueryTarget:
    command: str
    left_tab: str
    right_tab: Optional[str]
    description: str
    scope_selector: Optional[str] = None


@dataclass
class PageCapture:
    page: int
    request_url: Optional[str]
    payload: Dict[str, Any]

    @property
    def records(self) -> List[Dict[str, Any]]:
        data = self.payload.get("data")
        if isinstance(data, dict):
            records = data.get("records")
            if isinstance(records, list):
                return [item for item in records if isinstance(item, dict)]
        records = self.payload.get("records")
        if isinstance(records, list):
            return [item for item in records if isinstance(item, dict)]
        return []


@dataclass
class QueryRunResult:
    command: str
    description: str
    records: List[Dict[str, Any]] = field(default_factory=list)
    applied_filters: Dict[str, Any] = field(default_factory=dict)
    years_queried: List[int] = field(default_factory=list)
    pages_visited: int = 0
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "command": self.command,
            "description": self.description,
            "records": self.records,
            "metadata": {
                "generated_at": self.generated_at,
                "applied_filters": self.applied_filters,
                "pages_visited": self.pages_visited,
                "years_queried": self.years_queried,
                "total_records": len(self.records),
            },
        }
