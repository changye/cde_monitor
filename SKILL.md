---
name: cde-monitor
description: Query CDE China drug review public data for breakthrough therapy announcements, priority review announcements, included lists by company or drug, and in-review registration lookups by company or drug.
homepage: https://www.cde.org.cn
metadata: {"openclaw":{"emoji":"💊","homepage":"https://www.cde.org.cn","requires":{"anyBins":["python","python3","py"]},"os":["win32","linux"]}}
---

# CDE Monitor

Use this skill when the user needs live information from the China Center for Drug Evaluation site and the answer depends on current CDE public listings rather than static knowledge.

## Use Cases

- Breakthrough therapy: list drugs currently in 拟突破性治疗品种 announcements.
- Breakthrough therapy: find which drugs from a company are already in 纳入突破性治疗品种名单.
- Breakthrough therapy: find whether a drug appears in 纳入突破性治疗品种名单.
- Priority review: list drugs currently in 拟优先审评品种公示 announcements.
- Priority review: find which drugs from a company are already in 纳入优先审评品种名单.
- Priority review: find whether a drug appears in 纳入优先审评品种名单.
- In-review catalog: find CDE registration items for a company across years 2025 and 2026.
- In-review catalog: find CDE registration items for a drug across years 2025 and 2026.

## Name Confirmation Rule

For company-specific or drug-specific lookups, first confirm the exact company or drug name if the user input could be ambiguous, abbreviated, or misspelled. CDE matching is strict. If the user already provided a precise name and there is no ambiguity, proceed directly.

## Command Surface

Run the Python CLI from this skill directory.

```bash
python {baseDir}/scripts/cde_query.py breakthrough-announcements
python {baseDir}/scripts/cde_query.py breakthrough-included-by-company --company "<公司名>"
python {baseDir}/scripts/cde_query.py breakthrough-included-by-drug --drug "<药品名>"
python {baseDir}/scripts/cde_query.py priority-announcements
python {baseDir}/scripts/cde_query.py priority-included-by-company --company "<公司名>"
python {baseDir}/scripts/cde_query.py priority-included-by-drug --drug "<药品名>"
python {baseDir}/scripts/cde_query.py in-review-by-company --company "<公司名>" --years 2025 2026
python {baseDir}/scripts/cde_query.py in-review-by-drug --drug "<药品名>" --years 2025 2026
```

Add `--show-browser` when you need visible browser debugging. JSON is the default output. Use `--pretty` only when you want a human-readable terminal summary during debugging. Use `--max-pages <n>` only for debugging or validation; omit it for the full production query.

## Response Handling

- Read `records` for the merged deduplicated results.
- Use each record's `normalized` object for answering. It exposes stable keys such as `drug_name`, `company_name`, `acceptance_no`, `publication_title`, `year`, `source_menu`, and `source_tab`.
- Use `metadata.total_records`, `metadata.pages_visited`, `metadata.years_queried`, and `metadata.applied_filters` to summarize scope.
- The final user-facing answer should be a Markdown table whenever records are returned.
- Prefer a compact table with columns such as `药品名称`, `企业名称`, `受理号`, and `年份`. Add a short summary line above the table for `total_records`, `pages_visited`, and the applied filters when helpful.
- If the command returns no records, tell the user that no matching public CDE entries were found for the confirmed query.

## Failure Handling

- If Python or Selenium is missing, load [setup](./references/setup.md).
- If the site structure changes or the query fails, report that the live CDE page could not be parsed reliably and include the command error summary.
- Do not invent results when the command fails.

## References

- [Setup](./references/setup.md)
- [Queries](./references/queries.md)
- [Publish checklist](./references/publish-checklist.md)
