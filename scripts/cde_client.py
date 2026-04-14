from __future__ import annotations

import json
import math
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

from models import PageCapture, QueryRunResult, QueryTarget
from normalizers import dedupe_records, normalize_record


INFO_DISCLOSURE_URL = "https://www.cde.org.cn/main/xxgk/listpage/9f9c74c73e0f8f56a8bfbc646055026d"

BREAKTHROUGH_ANNOUNCEMENTS = QueryTarget(
    command="breakthrough-announcements",
    left_tab="突破性治疗公示",
    right_tab="拟突破性治疗品种",
    description="List all drugs currently shown in 拟突破性治疗品种.",
    scope_selector="#breakthroughTherapyTab",
)

BREAKTHROUGH_INCLUDED = QueryTarget(
    command="breakthrough-included-by-company",
    left_tab="突破性治疗公示",
    right_tab="纳入突破性治疗品种名单",
    description="Find company-specific drugs in 纳入突破性治疗品种名单.",
    scope_selector="#breakthroughTherapyTab",
)

BREAKTHROUGH_INCLUDED_BY_DRUG = QueryTarget(
    command="breakthrough-included-by-drug",
    left_tab="突破性治疗公示",
    right_tab="纳入突破性治疗品种名单",
    description="Find drug-specific records in 纳入突破性治疗品种名单.",
    scope_selector="#breakthroughTherapyTab",
)

PRIORITY_ANNOUNCEMENTS = QueryTarget(
    command="priority-announcements",
    left_tab="优先审评公示",
    right_tab="拟优先审评品种公示",
    description="List all drugs currently shown in 拟优先审评品种公示.",
    scope_selector="#priorityReviewTab",
)

PRIORITY_INCLUDED = QueryTarget(
    command="priority-included-by-company",
    left_tab="优先审评公示",
    right_tab="纳入优先审评品种名单",
    description="Find company-specific drugs in 纳入优先审评品种名单.",
    scope_selector="#priorityReviewTab",
)

PRIORITY_INCLUDED_BY_DRUG = QueryTarget(
    command="priority-included-by-drug",
    left_tab="优先审评公示",
    right_tab="纳入优先审评品种名单",
    description="Find drug-specific records in 纳入优先审评品种名单.",
    scope_selector="#priorityReviewTab",
)

IN_REVIEW = QueryTarget(
    command="in-review",
    left_tab="受理品种信息",
    right_tab="在审品种目录浏览",
    description="Query the in-review registration catalog.",
    scope_selector="#content_9f9c74c73e0f8f56a8bfbc646055026d",
)


class CDEQueryError(RuntimeError):
    pass


TEXT_FILTER_HINTS = {
    "受理号": ("acceptid", "acceptidInclude", "acceptidPlan", "acceptidBreakInclude", "acceptidBreakPlan"),
    "药品名称": ("drugname", "drugnameInclude", "drugnamePlan", "drugnameBreakInclude", "drugnameBreakPlan"),
    "企业名称": ("company",),
    "注册申请人": (
        "companyInclude",
        "companyPlan",
        "companyBreakInclude",
        "companyBreakPlan",
        "company",
    ),
}

SELECT_FILTER_HINTS = {
    "年度": ("year",),
    "药品类型": ("drugtype", "drugtypeNewReport"),
    "申请类型": ("applytype", "applytypecdeNewReport", "applytypecdeNewReportZy", "applytypecdeNewReportSw"),
}


class CDEClient:
    def __init__(self, headless: bool = True, timeout: int = 25, max_pages: Optional[int] = None) -> None:
        self.headless = headless
        self.timeout = timeout
        self.max_pages = max_pages

    def query_breakthrough_announcements(self) -> Dict[str, Any]:
        return self._query_target(BREAKTHROUGH_ANNOUNCEMENTS).to_dict()

    def query_breakthrough_included_by_company(self, company: str) -> Dict[str, Any]:
        self._validate_exact_name(company, "company")
        return self._query_target(
            BREAKTHROUGH_INCLUDED,
            text_filters=(("注册申请人", company),),
            applied_filters={"company": company},
        ).to_dict()

    def query_breakthrough_included_by_drug(self, drug: str) -> Dict[str, Any]:
        self._validate_exact_name(drug, "drug")
        return self._query_target(
            BREAKTHROUGH_INCLUDED_BY_DRUG,
            text_filters=(("药品名称", drug),),
            applied_filters={"drug": drug},
        ).to_dict()

    def query_priority_announcements(self) -> Dict[str, Any]:
        return self._query_target(PRIORITY_ANNOUNCEMENTS).to_dict()

    def query_priority_included_by_company(self, company: str) -> Dict[str, Any]:
        self._validate_exact_name(company, "company")
        return self._query_target(
            PRIORITY_INCLUDED,
            text_filters=(("注册申请人", company),),
            applied_filters={"company": company},
        ).to_dict()

    def query_priority_included_by_drug(self, drug: str) -> Dict[str, Any]:
        self._validate_exact_name(drug, "drug")
        return self._query_target(
            PRIORITY_INCLUDED_BY_DRUG,
            text_filters=(("药品名称", drug),),
            applied_filters={"drug": drug},
        ).to_dict()

    def query_in_review_by_company(self, company: str, years: Sequence[int]) -> Dict[str, Any]:
        self._validate_exact_name(company, "company")
        return self._query_in_review(
            text_filter_label="企业名称",
            text_filter_value=company,
            filter_key="company",
            years=years,
        ).to_dict()

    def query_in_review_by_drug(self, drug: str, years: Sequence[int]) -> Dict[str, Any]:
        self._validate_exact_name(drug, "drug")
        return self._query_in_review(
            text_filter_label="药品名称",
            text_filter_value=drug,
            filter_key="drug",
            years=years,
        ).to_dict()

    def _query_in_review(
        self,
        *,
        text_filter_label: str,
        text_filter_value: str,
        filter_key: str,
        years: Sequence[int],
    ) -> QueryRunResult:
        merged_records: List[Dict[str, Any]] = []
        total_pages = 0
        queried_years: List[int] = []
        for year in years:
            partial = self._query_target(
                IN_REVIEW,
                text_filters=((text_filter_label, text_filter_value),),
                select_filters=(("年度", str(year)),),
                applied_filters={filter_key: text_filter_value, "year": year},
                year=year,
            )
            merged_records.extend(partial.records)
            total_pages += partial.pages_visited
            queried_years.append(year)
        deduped = dedupe_records(merged_records)
        return QueryRunResult(
            command=f"in-review-by-{filter_key}",
            description=IN_REVIEW.description,
            records=deduped,
            applied_filters={filter_key: text_filter_value},
            years_queried=queried_years,
            pages_visited=total_pages,
        )

    def _query_target(
        self,
        target: QueryTarget,
        *,
        text_filters: Iterable[Tuple[str, str]] = (),
        select_filters: Iterable[Tuple[str, str]] = (),
        applied_filters: Optional[Dict[str, Any]] = None,
        year: Optional[int] = None,
    ) -> QueryRunResult:
        driver = self._build_driver()
        try:
            self._open_listing_page(driver)
            self._clear_logs(driver)
            self._click_left_tab(driver, target.left_tab)
            if target.right_tab:
                self._clear_logs(driver)
                self._click_right_tab(driver, target.right_tab, scope_selector=target.scope_selector)

            if text_filters or select_filters:
                self._clear_logs(driver)
                for label, value in select_filters:
                    self._select_filter(driver, label, value, scope_selector=target.scope_selector)
                for label, value in text_filters:
                    self._fill_text_filter(driver, label, value, scope_selector=target.scope_selector)
                self._submit_search(driver, scope_selector=target.scope_selector)

            first_page = self._wait_for_payload(driver, page=1)
            total_pages = self._detect_total_pages(driver, first_page, scope_selector=target.scope_selector)
            if self.max_pages is not None:
                total_pages = min(total_pages, max(1, self.max_pages))

            records = [
                normalize_record(
                    raw_record,
                    source_menu=target.left_tab,
                    source_tab=target.right_tab or target.left_tab,
                    page=1,
                    year=year,
                )
                for raw_record in first_page.records
            ]
            pages_visited = 1
            seen_page_keys = {self._page_key(first_page.records)}

            for page in range(2, total_pages + 1):
                self._clear_logs(driver)
                if not self._go_to_page(driver, page, scope_selector=target.scope_selector):
                    break
                capture = self._wait_for_payload(driver, page=page)
                page_key = self._page_key(capture.records)
                if not capture.records or page_key in seen_page_keys:
                    break
                seen_page_keys.add(page_key)
                pages_visited += 1
                records.extend(
                    normalize_record(
                        raw_record,
                        source_menu=target.left_tab,
                        source_tab=target.right_tab or target.left_tab,
                        page=page,
                        year=year,
                    )
                    for raw_record in capture.records
                )

            return QueryRunResult(
                command=target.command,
                description=target.description,
                records=dedupe_records(records),
                applied_filters=applied_filters or {},
                years_queried=[year] if year is not None else [],
                pages_visited=pages_visited,
            )
        finally:
            driver.quit()

    def _build_driver(self) -> webdriver.Chrome:
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--window-size=1440,1200")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--lang=zh-CN")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        )
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        try:
            driver = webdriver.Chrome(options=options)
        except WebDriverException as exc:
            raise CDEQueryError(
                "Could not start Chrome via Selenium. Check Chrome installation and local driver support."
            ) from exc
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en-US', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4]});
                """
            },
        )
        return driver

    def _open_listing_page(self, driver: webdriver.Chrome) -> None:
        driver.get(INFO_DISCLOSURE_URL)
        WebDriverWait(driver, self.timeout).until(
            lambda current_driver: current_driver.execute_script("return document.readyState") == "complete"
        )
        time.sleep(1.5)

    def _click_left_tab(self, driver: webdriver.Chrome, text: str) -> None:
        if not self._click_element_by_exact_text(driver, text, exclude_left=False):
            raise CDEQueryError(f"Could not find left navigation tab: {text}")
        time.sleep(1.5)

    def _click_right_tab(self, driver: webdriver.Chrome, text: str, *, scope_selector: Optional[str] = None) -> None:
        if not self._click_element_by_exact_text(driver, text, exclude_left=True, scope_selector=scope_selector):
            raise CDEQueryError(f"Could not find right-side tab: {text}")
        time.sleep(1.5)

    def _click_element_by_exact_text(
        self,
        driver: webdriver.Chrome,
        text: str,
        *,
        exclude_left: bool,
        scope_selector: Optional[str] = None,
    ) -> bool:
        script = """
        const targetText = arguments[0];
        const excludeLeft = arguments[1];
        const scopeSelector = arguments[2];
        const scope = scopeSelector ? document.querySelector(scopeSelector) : document;
        const elements = (scope || document).querySelectorAll('a, span, button, li, div');
        const leftSelectors = '.left-nav, .sidebar, .menu-list, .el-menu, [class*="left"]';
        const normalize = (value) => (value || '').replace(/\s+/g, '').replace(/[：:]/g, '').trim();
        const normalizedTarget = normalize(targetText);
        let containsMatch = null;
        for (const element of elements) {
            const content = normalize(element.textContent || '');
            if (!content) continue;
            if (excludeLeft && element.closest(leftSelectors)) continue;
            if (content === normalizedTarget) {
                element.click();
                return true;
            }
            if (content.includes(normalizedTarget) || normalizedTarget.includes(content)) {
                if (!containsMatch || content.length < containsMatch.content.length) {
                    containsMatch = { element, content };
                }
            }
        }
        if (containsMatch) {
            containsMatch.element.click();
            return true;
        }
        return false;
        """
        return bool(driver.execute_script(script, text, exclude_left, scope_selector))

    def _fill_text_filter(
        self,
        driver: webdriver.Chrome,
        label: str,
        value: str,
        *,
        scope_selector: Optional[str] = None,
    ) -> None:
        script = """
        const labelText = arguments[0];
        const targetValue = arguments[1];
        const scopeSelector = arguments[2];
                const preferredIds = arguments[3] || [];
        const scopeRoot = scopeSelector ? document.querySelector(scopeSelector) : document;
        const scope = scopeRoot && scopeRoot.querySelector('.layui-tab-content .layui-show')
          ? scopeRoot.querySelector('.layui-tab-content .layui-show')
          : (scopeRoot || document);
                const setValue = (input, currentValue) => {
                    const descriptor = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
                    if (descriptor && descriptor.set) {
                        descriptor.set.call(input, currentValue);
                    } else {
                        input.value = currentValue;
                    }
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                };
                for (const preferredId of preferredIds) {
                    const escapedId = window.CSS && CSS.escape ? CSS.escape(preferredId) : preferredId;
                    const direct = scope.querySelector(`#${escapedId}`) || scope.querySelector(`input[name="${preferredId}"], textarea[name="${preferredId}"]`);
                    if (direct) {
                        setValue(direct, targetValue);
                        return true;
                    }
                }
        const candidates = scope.querySelectorAll('label, span, div, td, th');
        const matchLabel = (text) => text && text.replace(/[:：]/g, '').trim().includes(labelText);
        for (const candidate of candidates) {
          const text = (candidate.textContent || '').trim();
          if (!text || text.length > 40) continue;
          if (!matchLabel(text)) continue;
          let node = candidate;
          for (let depth = 0; depth < 4 && node; depth += 1) {
            const input = node.querySelector('input, textarea');
            if (input) {
              setValue(input, targetValue);
              return true;
            }
            node = node.parentElement;
          }
        }
        return false;
        """
        preferred_ids = list(TEXT_FILTER_HINTS.get(label, ()))
        if not driver.execute_script(script, label, value, scope_selector, preferred_ids):
            raise CDEQueryError(f"Could not find text filter labeled {label}")
        time.sleep(0.4)

    def _select_filter(
        self,
        driver: webdriver.Chrome,
        label: str,
        value: str,
        *,
        scope_selector: Optional[str] = None,
    ) -> None:
        script = """
        const labelText = arguments[0];
        const targetValue = arguments[1];
        const scopeSelector = arguments[2];
                const preferredIds = arguments[3] || [];
        const scopeRoot = scopeSelector ? document.querySelector(scopeSelector) : document;
        const scope = scopeRoot && scopeRoot.querySelector('.layui-tab-content .layui-show')
          ? scopeRoot.querySelector('.layui-tab-content .layui-show')
          : (scopeRoot || document);
                const setSelectValue = (select) => {
                    for (const option of select.options) {
                        const optionText = (option.textContent || '').trim();
                        if (optionText === targetValue || option.value === targetValue) {
                            select.value = option.value;
                            select.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                    }
                    return false;
                };
                for (const preferredId of preferredIds) {
                    const escapedId = window.CSS && CSS.escape ? CSS.escape(preferredId) : preferredId;
                    const direct = scope.querySelector(`#${escapedId}`) || scope.querySelector(`select[name="${preferredId}"]`);
                    if (direct && setSelectValue(direct)) {
                        return true;
                    }
                }
        const candidates = scope.querySelectorAll('label, span, div, td, th');
        const matchLabel = (text) => text && text.replace(/[:：]/g, '').trim().includes(labelText);
        for (const candidate of candidates) {
            const text = (candidate.textContent || '').trim();
            if (!text || text.length > 40) continue;
            if (!matchLabel(text)) continue;
            let node = candidate;
            for (let depth = 0; depth < 4 && node; depth += 1) {
                const select = node.querySelector('select');
                if (select && setSelectValue(select)) {
                    return true;
                }
                node = node.parentElement;
            }
        }
        return false;
        """
        preferred_ids = list(SELECT_FILTER_HINTS.get(label, ()))
        if not driver.execute_script(script, label, value, scope_selector, preferred_ids):
            raise CDEQueryError(f"Could not find select filter labeled {label}")
        time.sleep(0.4)

    def _submit_search(self, driver: webdriver.Chrome, *, scope_selector: Optional[str] = None) -> None:
        script = """
        const scopeSelector = arguments[0];
        const scopeRoot = scopeSelector ? document.querySelector(scopeSelector) : document;
        const scope = scopeRoot && scopeRoot.querySelector('.layui-tab-content .layui-show')
          ? scopeRoot.querySelector('.layui-tab-content .layui-show')
          : (scopeRoot || document);
                const candidates = Array.from(scope.querySelectorAll('button, a, span, div'));
        const labels = ['查询', '查找', '搜索'];
                const score = (candidate) => {
                    let current = 0;
                    if (candidate.tagName === 'BUTTON') current += 100;
                    if (candidate.tagName === 'A') current += 80;
                    if (candidate.getAttribute('onclick')) current += 40;
                    if ((candidate.className || '').includes('searchBtn')) current += 20;
                    return current;
                };
                candidates.sort((left, right) => score(right) - score(left));
                for (const candidate of candidates) {
          const text = (candidate.textContent || '').trim();
          if (!labels.includes(text)) continue;
          if (candidate.closest('.layui-laypage')) continue;
          candidate.click();
          return true;
        }
        return false;
        """
        if not driver.execute_script(script, scope_selector):
            raise CDEQueryError("Could not find the search button on the CDE page")
        time.sleep(1.5)

    def _wait_for_payload(self, driver: webdriver.Chrome, *, page: int) -> PageCapture:
        deadline = time.time() + self.timeout
        best_capture: Optional[PageCapture] = None
        best_size = -1
        while time.time() < deadline:
            logs = driver.get_log("performance")
            for entry in logs:
                capture = self._extract_capture_from_log(driver, entry, page)
                if capture is None:
                    continue
                size = len(capture.records)
                if size > best_size:
                    best_capture = capture
                    best_size = size
            if best_capture is not None:
                return best_capture
            time.sleep(0.3)
        raise CDEQueryError("Timed out while waiting for a CDE data response")

    def _extract_capture_from_log(
        self,
        driver: webdriver.Chrome,
        entry: Dict[str, Any],
        page: int,
    ) -> Optional[PageCapture]:
        try:
            message = json.loads(entry["message"]).get("message", {})
        except (KeyError, TypeError, json.JSONDecodeError):
            return None
        if message.get("method") != "Network.responseReceived":
            return None
        params = message.get("params", {})
        response = params.get("response", {})
        request_id = params.get("requestId")
        url = response.get("url", "")
        mime_type = response.get("mimeType", "")
        if not request_id or "cde.org.cn" not in url:
            return None
        if "json" not in mime_type.lower() and "api" not in url.lower() and "list" not in url.lower():
            return None
        try:
            body = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
        except WebDriverException:
            return None
        raw_body = body.get("body", "")
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            return None
        capture = PageCapture(page=page, request_url=url, payload=payload)
        if capture.records:
            return capture
        return None

    def _detect_total_pages(
        self,
        driver: webdriver.Chrome,
        first_page: PageCapture,
        *,
        scope_selector: Optional[str] = None,
    ) -> int:
        payload = first_page.payload.get("data") if isinstance(first_page.payload, dict) else None
        if isinstance(payload, dict):
            for key in ("pages", "totalPage", "pageCount"):
                value = payload.get(key)
                if isinstance(value, int) and value > 0:
                    return value
            total = payload.get("total")
            if isinstance(total, int) and total > 0 and first_page.records:
                page_size = payload.get("size") or len(first_page.records)
                if isinstance(page_size, int) and page_size > 0:
                    return max(1, math.ceil(total / page_size))

        script = """
        const scopeSelector = arguments[0];
        const scopeRoot = scopeSelector ? document.querySelector(scopeSelector) : document;
        const scope = scopeRoot && scopeRoot.querySelector('.layui-tab-content .layui-show')
          ? scopeRoot.querySelector('.layui-tab-content .layui-show')
          : (scopeRoot || document);
        const countNode = scope.querySelector('.layui-laypage-count');
        if (countNode) {
          const match = countNode.textContent.match(/共\s*(\d+)\s*条/);
          if (match) {
            const limits = Array.from(scope.querySelectorAll('.layui-laypage-limits option')).map((option) => ({
              selected: option.selected,
              value: parseInt(option.value || option.textContent, 10),
            }));
            const selectedLimit = limits.find((item) => !Number.isNaN(item.value) && item.selected);
            return { total: parseInt(match[1], 10), pageSize: selectedLimit ? selectedLimit.value : 10 };
          }
        }
        const buttons = scope.querySelectorAll('.layui-laypage a');
        let maxPage = 1;
        for (const button of buttons) {
          const value = parseInt((button.textContent || '').trim(), 10);
          if (!Number.isNaN(value) && value > maxPage) {
            maxPage = value;
          }
        }
        return { maxPage };
        """
        info = driver.execute_script(script, scope_selector)
        if isinstance(info, dict):
            total = info.get("total")
            page_size = info.get("pageSize") or 10
            if isinstance(total, int) and total > 0:
                return max(1, math.ceil(total / page_size))
            max_page = info.get("maxPage")
            if isinstance(max_page, int) and max_page > 0:
                return max_page
        return 1

    def _go_to_page(self, driver: webdriver.Chrome, page: int, *, scope_selector: Optional[str] = None) -> bool:
        script = """
        const pageNumber = String(arguments[0]);
        const scopeSelector = arguments[1];
        const scopeRoot = scopeSelector ? document.querySelector(scopeSelector) : document;
        const scope = scopeRoot && scopeRoot.querySelector('.layui-tab-content .layui-show')
          ? scopeRoot.querySelector('.layui-tab-content .layui-show')
          : (scopeRoot || document);
        let input = null;
        const skipDiv = scope.querySelector('.layui-laypage-skip');
        if (skipDiv) {
          input = skipDiv.querySelector('input.layui-input');
        }
        if (!input) {
          const inputs = scope.querySelectorAll('input.layui-input');
          for (const candidate of inputs) {
            const parentText = candidate.parentElement ? candidate.parentElement.textContent : '';
            if (parentText && parentText.includes('到第') && parentText.includes('页')) {
              input = candidate;
              break;
            }
          }
        }
        if (!input) {
          return false;
        }
        const descriptor = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
        if (descriptor && descriptor.set) {
          descriptor.set.call(input, pageNumber);
        } else {
          input.value = pageNumber;
        }
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        const button = scope.querySelector('.layui-laypage-btn');
        if (!button) {
          return false;
        }
        button.click();
        return true;
        """
        success = bool(driver.execute_script(script, page, scope_selector))
        if success:
            time.sleep(1.5)
        return success

    def _clear_logs(self, driver: webdriver.Chrome) -> None:
        try:
            driver.get_log("performance")
        except WebDriverException:
            return

    def _page_key(self, records: List[Dict[str, Any]]) -> str:
        return json.dumps(records, ensure_ascii=False, sort_keys=True)

    def _validate_exact_name(self, value: str, label: str) -> None:
        if not value or not value.strip():
            raise CDEQueryError(f"A non-empty {label} name is required")
