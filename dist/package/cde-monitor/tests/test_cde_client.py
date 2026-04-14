from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from cde_client import CDEClient, IN_REVIEW
from models import PageCapture


class _FakeDriver:
    def quit(self) -> None:
        return


class _PaginationClient(CDEClient):
    def __init__(self, page_records: List[List[Dict[str, Any]]]) -> None:
        super().__init__(headless=True, timeout=1)
        self._page_records = page_records

    def _build_driver(self) -> _FakeDriver:
        return _FakeDriver()

    def _open_listing_page(self, driver: _FakeDriver) -> None:
        return

    def _clear_logs(self, driver: _FakeDriver) -> None:
        return

    def _click_left_tab(self, driver: _FakeDriver, text: str) -> None:
        return

    def _click_right_tab(self, driver: _FakeDriver, text: str, *, scope_selector=None) -> None:
        return

    def _fill_text_filter(self, driver: _FakeDriver, label: str, value: str, *, scope_selector=None) -> None:
        return

    def _select_filter(self, driver: _FakeDriver, label: str, value: str, *, scope_selector=None) -> None:
        return

    def _submit_search(self, driver: _FakeDriver, *, scope_selector=None) -> None:
        return

    def _wait_for_payload(self, driver: _FakeDriver, *, page: int) -> PageCapture:
        records = self._page_records[page - 1]
        payload = {
            "data": {
                "records": records,
                "pages": len(self._page_records),
                "total": sum(len(current_page) for current_page in self._page_records),
                "size": 10,
            }
        }
        return PageCapture(page=page, request_url=f"mock://page/{page}", payload=payload)

    def _detect_total_pages(self, driver: _FakeDriver, first_page: PageCapture, *, scope_selector=None) -> int:
        return len(self._page_records)

    def _go_to_page(self, driver: _FakeDriver, page: int, *, scope_selector=None) -> bool:
        return 1 <= page <= len(self._page_records)


class CDEClientPaginationTest(unittest.TestCase):
    def test_in_review_company_query_aggregates_four_pages(self) -> None:
        page_records = []
        acceptance_index = 0
        for page_size in (10, 10, 10, 8):
            current_page = []
            for _ in range(page_size):
                acceptance_index += 1
                current_page.append(
                    {
                        "acceptid": f"MSD-{acceptance_index:03d}",
                        "drgnamecn": f"示例药物{acceptance_index}",
                        "companys": "默沙东",
                        "createdate": "2026-04-14",
                    }
                )
            page_records.append(current_page)

        client = _PaginationClient(page_records)

        result = client.query_in_review_by_company("默沙东", [2026])

        self.assertTrue(result["ok"])
        self.assertEqual(result["metadata"]["total_records"], 38)
        self.assertEqual(result["metadata"]["pages_visited"], 4)
        self.assertEqual(result["metadata"]["years_queried"], [2026])
        self.assertEqual(result["metadata"]["applied_filters"], {"company": "默沙东"})
        self.assertEqual(result["records"][0]["normalized"]["acceptance_no"], "MSD-001")
        self.assertEqual(result["records"][-1]["normalized"]["acceptance_no"], "MSD-038")


if __name__ == "__main__":
    unittest.main()