from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from cde_query import build_parser


class CliParserTest(unittest.TestCase):
    def test_global_flags_work_after_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "breakthrough-announcements",
            "--pretty",
            "--timeout",
            "30",
            "--max-pages",
            "2",
        ])
        self.assertTrue(args.pretty)
        self.assertEqual(args.timeout, 30)
        self.assertEqual(args.max_pages, 2)

    def test_company_command_requires_name(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "priority-included-by-company",
            "--company",
            "示例企业",
        ])
        self.assertEqual(args.command, "priority-included-by-company")
        self.assertEqual(args.company, "示例企业")

    def test_drug_commands_require_drug_name(self) -> None:
        parser = build_parser()
        breakthrough_args = parser.parse_args([
            "breakthrough-included-by-drug",
            "--drug",
            "帕博利珠单抗",
        ])
        priority_args = parser.parse_args([
            "priority-included-by-drug",
            "--drug",
            "帕博利珠单抗",
        ])
        self.assertEqual(breakthrough_args.command, "breakthrough-included-by-drug")
        self.assertEqual(breakthrough_args.drug, "帕博利珠单抗")
        self.assertEqual(priority_args.command, "priority-included-by-drug")
        self.assertEqual(priority_args.drug, "帕博利珠单抗")

    def test_in_review_defaults_years(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "in-review-by-drug",
            "--drug",
            "示例药物",
        ])
        self.assertEqual(args.years, list(range(2016, 2027)))

    def test_in_review_rejects_year_before_supported_range(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([
                "in-review-by-company",
                "--company",
                "示例企业",
                "--years",
                "2015",
            ])

    def test_in_review_rejects_year_after_supported_range(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([
                "in-review-by-drug",
                "--drug",
                "示例药物",
                "--years",
                "2027",
            ])

    def test_review_status_command_requires_acceptance_number(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "review-status-by-acceptance-no",
            "--acceptance-no",
            "CYSB2600096",
        ])
        self.assertEqual(args.command, "review-status-by-acceptance-no")
        self.assertEqual(args.acceptance_no, "CYSB2600096")


if __name__ == "__main__":
    unittest.main()