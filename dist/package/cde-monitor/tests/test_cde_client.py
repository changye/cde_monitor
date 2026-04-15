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


class _ReviewLookupClient(CDEClient):
    def __init__(self, basic_record: Dict[str, Any] | None, attempt_results: List[Dict[str, Any]]) -> None:
        super().__init__(headless=True, timeout=1)
        self._basic_record = basic_record
        self._attempt_results = list(attempt_results)
        self.calls: List[Dict[str, Any]] = []

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

    def _query_acceptance_basic_info(self, acceptance_no: str) -> Dict[str, Any] | None:
        return self._basic_record

    def _run_review_status_attempt(
        self,
        driver: _FakeDriver,
        acceptance_no: str,
        plan: Dict[str, Any],
        *,
        use_acceptance_filter: bool,
    ) -> Dict[str, Any]:
        self.calls.append({
            "acceptance_no": acceptance_no,
            "plan": plan,
            "use_acceptance_filter": use_acceptance_filter,
        })
        return self._attempt_results.pop(0)


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

    def test_in_review_empty_results_are_not_treated_as_timeout(self) -> None:
        client = _PaginationClient([[]])

        result = client.query_in_review_by_company("同源康医药", [2024])

        self.assertTrue(result["ok"])
        self.assertEqual(result["metadata"]["total_records"], 0)
        self.assertEqual(result["metadata"]["pages_visited"], 1)
        self.assertEqual(result["metadata"]["years_queried"], [2024])
        self.assertEqual(result["metadata"]["applied_filters"], {"company": "同源康医药"})
        self.assertEqual(result["records"], [])


class CDEClientReviewLookupTest(unittest.TestCase):
    def test_infer_acceptance_year_uses_digits_after_prefix(self) -> None:
        self.assertEqual(CDEClient.infer_acceptance_year("CYSB2600096"), 2026)
        self.assertEqual(CDEClient.infer_acceptance_year("CXHL0500001"), 2005)

    def test_review_lookup_rejects_year_outside_supported_page_range(self) -> None:
        client = _ReviewLookupClient(None, [])

        with self.assertRaisesRegex(Exception, "该受理号推断年份超出当前 CDE 页面可查询范围"):
            client.query_review_status_by_acceptance_no("CYHS2804599")

    def test_review_lookup_returns_basic_info_missing_when_first_step_fails(self) -> None:
        client = _ReviewLookupClient(None, [])

        result = client.query_review_status_by_acceptance_no("CYSB2600096")

        self.assertTrue(result["ok"])
        self.assertFalse(result["basic_info_found"])
        self.assertFalse(result["review_status_found"])
        self.assertEqual(result["attempts"], [])

    def test_review_lookup_retries_without_acceptance_filter_after_warning(self) -> None:
        basic_record = {
            "normalized": {
                "acceptance_no": "CYSB2600096",
                "drug_name": "依沃西单抗注射液",
                "company_name": "康方赛诺医药有限公司",
                "drug_type": "治疗用生物制品",
                "application_type": "补充申请",
            },
            "raw": {},
        }
        client = _ReviewLookupClient(
            basic_record,
            [
                {
                    "attempt": {
                        "public_type": "生物制品审评序列公示",
                        "task_category": "补充申请",
                        "biologics_subtype": "治疗用生物制品",
                        "used_acceptance_filter": True,
                        "warning": "没有查到受理号为【CYSB2600096】的数据！",
                        "pages_scanned": 1,
                        "found": False,
                    },
                    "review_status": None,
                },
                {
                    "attempt": {
                        "public_type": "生物制品审评序列公示",
                        "task_category": "补充申请",
                        "biologics_subtype": "治疗用生物制品",
                        "used_acceptance_filter": False,
                        "warning": "",
                        "pages_scanned": 33,
                        "found": True,
                    },
                    "review_status": {
                        "acceptance_no": "CYSB2600096",
                        "review_state": "排队待审评",
                        "entered_center_at": "2026-03-13",
                        "stages": {
                            "药理毒理": {"code": 2, "label": "本专业排队待审评", "icon": "/main/img/lamp_y.jpg"},
                        },
                    },
                },
            ],
        )

        result = client.query_review_status_by_acceptance_no("CYSB2600096")

        self.assertTrue(result["basic_info_found"])
        self.assertTrue(result["review_status_found"])
        self.assertEqual(result["review_status"]["acceptance_no"], "CYSB2600096")
        self.assertEqual(result["metadata"]["pages_visited"], 34)
        self.assertEqual(len(client.calls), 2)
        self.assertTrue(client.calls[0]["use_acceptance_filter"])
        self.assertFalse(client.calls[1]["use_acceptance_filter"])


if __name__ == "__main__":
    unittest.main()