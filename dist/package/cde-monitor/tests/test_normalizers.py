from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from normalizers import dedupe_records, normalize_record


class NormalizersTest(unittest.TestCase):
    def test_normalize_record_maps_common_fields(self) -> None:
        record = {
            "drgnamecn": "示例药物",
            "company": "示例企业",
            "acceptid": "CXHS123",
            "publicDate": "2026-04-14",
        }
        result = normalize_record(
            record,
            source_menu="突破性治疗公示",
            source_tab="拟突破性治疗品种",
            page=1,
        )
        normalized = result["normalized"]
        self.assertEqual(normalized["drug_name"], "示例药物")
        self.assertEqual(normalized["company_name"], "示例企业")
        self.assertEqual(normalized["acceptance_no"], "CXHS123")
        self.assertEqual(normalized["drug_type"], None)
        self.assertEqual(normalized["application_type"], None)
        self.assertEqual(normalized["year"], 2026)

    def test_normalize_record_maps_review_lookup_fields(self) -> None:
        record = {
            "acceptid": "CYSB2600096",
            "drgnamecn": "依沃西单抗注射液",
            "companys": "康方赛诺医药有限公司;",
            "drugtype": "治疗用生物制品",
            "applytype": "补充申请",
            "registerkind": "1",
            "createdate": "2026-03-13",
        }
        result = normalize_record(
            record,
            source_menu="受理品种信息",
            source_tab="在审品种目录浏览",
            page=1,
            year=2026,
        )
        normalized = result["normalized"]
        self.assertEqual(normalized["drug_type"], "治疗用生物制品")
        self.assertEqual(normalized["application_type"], "补充申请")
        self.assertEqual(normalized["registration_category"], "1")
        self.assertEqual(normalized["publication_date"], "2026-03-13")

    def test_dedupe_records_uses_normalized_fingerprint(self) -> None:
        first = normalize_record(
            {"drgnamecn": "示例药物", "company": "示例企业", "acceptid": "A-1"},
            source_menu="优先审评公示",
            source_tab="纳入优先审评品种名单",
            page=1,
        )
        duplicate = normalize_record(
            {"drgnamecn": "示例药物", "company": "示例企业", "acceptid": "A-1"},
            source_menu="优先审评公示",
            source_tab="纳入优先审评品种名单",
            page=2,
        )
        deduped = dedupe_records([first, duplicate])
        self.assertEqual(len(deduped), 1)

    def test_dedupe_records_preserves_distinct_backend_ids(self) -> None:
        first = normalize_record(
            {"drgnamecn": "示例药物", "company": "示例企业", "acceptid": "无", "paidCODE": "ID-1"},
            source_menu="优先审评公示",
            source_tab="拟优先审评品种公示",
            page=1,
        )
        second = normalize_record(
            {"drgnamecn": "示例药物", "company": "示例企业", "acceptid": "无", "paidCODE": "ID-2"},
            source_menu="优先审评公示",
            source_tab="拟优先审评品种公示",
            page=1,
        )
        deduped = dedupe_records([first, second])
        self.assertEqual(len(deduped), 2)


if __name__ == "__main__":
    unittest.main()
