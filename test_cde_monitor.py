"""
CDEDataFetcher 单元测试

测试 cde_monitor.py 中 CDEDataFetcher 类的各个方法。
由于 get_data_from_page 依赖 Selenium 浏览器，所有与浏览器交互的部分都通过
unittest.mock 进行模拟，不会实际访问网络或启动浏览器。
"""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch, call

from cde_monitor import CDEDataFetcher


class TestCDEDataFetcherInit(unittest.TestCase):
    """测试 CDEDataFetcher 初始化"""

    def test_default_headless_is_false(self):
        fetcher = CDEDataFetcher()
        self.assertFalse(fetcher.headless)

    def test_custom_headless_true(self):
        fetcher = CDEDataFetcher(headless=True)
        self.assertTrue(fetcher.headless)

    def test_base_url(self):
        fetcher = CDEDataFetcher()
        self.assertEqual(fetcher.base_url, "https://www.cde.org.cn")


class TestShortcutMethods(unittest.TestCase):
    """测试所有快捷方法是否正确委托给 get_data_from_page"""

    def setUp(self):
        self.fetcher = CDEDataFetcher()
        self.fetcher.get_data_from_page = MagicMock(return_value={"code": 200})

    def test_get_new_drug_acceptance_announcement_default_page(self):
        self.fetcher.get_new_drug_acceptance_announcement()
        self.fetcher.get_data_from_page.assert_called_once_with(
            "受理品种信息", "受理品种目录浏览", 1
        )

    def test_get_new_drug_acceptance_announcement_custom_page(self):
        self.fetcher.get_new_drug_acceptance_announcement(page=3)
        self.fetcher.get_data_from_page.assert_called_once_with(
            "受理品种信息", "受理品种目录浏览", 3
        )

    def test_get_new_drug_approving_info(self):
        self.fetcher.get_new_drug_approving_info(page=2)
        self.fetcher.get_data_from_page.assert_called_once_with(
            "受理品种信息", "在审品种目录浏览", 2
        )

    def test_get_priority_announcement(self):
        self.fetcher.get_priority_announcement(page=1)
        self.fetcher.get_data_from_page.assert_called_once_with(
            "优先审评公示", "拟优先审评品种公示", 1
        )

    def test_get_priority_approved_list(self):
        self.fetcher.get_priority_approved_list(page=4)
        self.fetcher.get_data_from_page.assert_called_once_with(
            "优先审评公示", "纳入优先审评品种名单", 4
        )

    def test_get_priority_dissent_results(self):
        self.fetcher.get_priority_dissent_results()
        self.fetcher.get_data_from_page.assert_called_once_with(
            "优先审评公示", "异议论证结果查询", 1
        )

    def test_get_breakthrough_therapy_announcement(self):
        self.fetcher.get_breakthrough_therapy_announcement()
        self.fetcher.get_data_from_page.assert_called_once_with(
            "突破性治疗公示", "拟突破性治疗品种", 1
        )

    def test_get_breakthrough_therapy_list(self):
        self.fetcher.get_breakthrough_therapy_list(page=2)
        self.fetcher.get_data_from_page.assert_called_once_with(
            "突破性治疗公示", "纳入突破性治疗品种名单", 2
        )

    def test_get_breakthrough_therapy_dissent_results(self):
        self.fetcher.get_breakthrough_therapy_dissent_results()
        self.fetcher.get_data_from_page.assert_called_once_with(
            "突破性治疗公示", "异议论证结果查询", 1
        )

    def test_get_communication_notice(self):
        self.fetcher.get_communication_notice(page=5)
        self.fetcher.get_data_from_page.assert_called_once_with(
            "沟通交流公示", "公示信息", 5
        )

    def test_shortcut_returns_value_from_get_data_from_page(self):
        expected = {"code": 200, "data": {"records": [{"id": 1}]}}
        self.fetcher.get_data_from_page.return_value = expected
        result = self.fetcher.get_priority_announcement()
        self.assertEqual(result, expected)


class TestSaveToJson(unittest.TestCase):
    """测试 save_to_json 方法"""

    def setUp(self):
        self.fetcher = CDEDataFetcher()
        self.tmpdir = tempfile.mkdtemp()

    def test_save_nonempty_records(self):
        records = [{"id": 1, "name": "药品A"}, {"id": 2, "name": "药品B"}]
        filepath = os.path.join(self.tmpdir, "out.json")
        self.fetcher.save_to_json(records, filepath)

        self.assertTrue(os.path.exists(filepath))
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data, records)

    def test_save_empty_records_does_not_create_file(self):
        filepath = os.path.join(self.tmpdir, "empty.json")
        self.fetcher.save_to_json([], filepath)
        self.assertFalse(os.path.exists(filepath))

    def test_chinese_characters_preserved(self):
        records = [{"药品名称": "阿司匹林", "企业": "某药厂"}]
        filepath = os.path.join(self.tmpdir, "chinese.json")
        self.fetcher.save_to_json(records, filepath)

        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("阿司匹林", content)
        self.assertIn("某药厂", content)


class TestSaveToExcel(unittest.TestCase):
    """测试 save_to_excel 方法"""

    def setUp(self):
        self.fetcher = CDEDataFetcher()
        self.tmpdir = tempfile.mkdtemp()

    def test_save_nonempty_records(self):
        import pandas as pd

        records = [{"id": 1, "name": "药品A"}, {"id": 2, "name": "药品B"}]
        filepath = os.path.join(self.tmpdir, "out.xlsx")
        self.fetcher.save_to_excel(records, filepath)

        self.assertTrue(os.path.exists(filepath))
        df = pd.read_excel(filepath)
        self.assertEqual(len(df), 2)
        self.assertListEqual(list(df.columns), ["id", "name"])

    def test_save_empty_records_does_not_create_file(self):
        filepath = os.path.join(self.tmpdir, "empty.xlsx")
        self.fetcher.save_to_excel([], filepath)
        self.assertFalse(os.path.exists(filepath))


class TestGetDataFromPage(unittest.TestCase):
    """测试 get_data_from_page 方法（通过 mock Selenium）

    由于 cde_monitor.py 在方法内部使用 `from selenium import webdriver`，
    需要 patch selenium 包本身的 webdriver 属性。
    """

    def _make_driver_mock(self, api_response: dict, menu_found: bool = True,
                          tab_click_result: str = "clicked span: 公示信息"):
        """构造一个模拟 Chrome WebDriver。"""
        driver = MagicMock()
        driver.get.return_value = None

        # execute_script 的返回值顺序：点击菜单 -> 点击 tab
        driver.execute_script.side_effect = [
            True if menu_found else False,  # 步骤2: 点击左侧菜单
            tab_click_result,               # 步骤3: 切换 tab
        ]

        # get_log('performance') 返回一条包含目标 API 响应的日志
        perf_log_entry = {
            "message": json.dumps({
                "message": {
                    "method": "Network.responseReceived",
                    "params": {
                        "requestId": "req-001",
                        "response": {
                            "url": "https://www.cde.org.cn/api/getMenuListHc",
                        },
                    },
                }
            })
        }
        driver.get_log.return_value = [perf_log_entry]

        # execute_cdp_cmd 返回 API body
        driver.execute_cdp_cmd.return_value = {
            "body": json.dumps(api_response)
        }
        return driver

    @patch("selenium.webdriver.Chrome")
    @patch("selenium.webdriver.ChromeOptions")
    def test_returns_data_on_success(self, mock_options_cls, mock_chrome_cls):
        api_response = {
            "code": 200,
            "data": {"records": [{"id": 1}], "total": 1},
        }
        driver = self._make_driver_mock(api_response)
        mock_options_cls.return_value = MagicMock()
        mock_chrome_cls.return_value = driver

        fetcher = CDEDataFetcher(headless=True)
        result = fetcher.get_data_from_page("优先审评公示", "公示信息", page=1)

        self.assertIsNotNone(result)
        self.assertEqual(result["code"], 200)
        self.assertIn("records", result["data"])
        driver.quit.assert_called_once()

    @patch("selenium.webdriver.Chrome")
    @patch("selenium.webdriver.ChromeOptions")
    def test_returns_none_when_menu_not_found(self, mock_options_cls, mock_chrome_cls):
        driver = MagicMock()
        driver.execute_script.return_value = False  # 未找到菜单
        mock_options_cls.return_value = MagicMock()
        mock_chrome_cls.return_value = driver

        fetcher = CDEDataFetcher(headless=True)
        result = fetcher.get_data_from_page("不存在的菜单", "某tab", page=1)

        self.assertIsNone(result)
        driver.quit.assert_called_once()

    @patch("selenium.webdriver.Chrome")
    @patch("selenium.webdriver.ChromeOptions")
    def test_driver_quit_called_on_exception(self, mock_options_cls, mock_chrome_cls):
        driver = MagicMock()
        driver.get.side_effect = Exception("网络错误")
        mock_options_cls.return_value = MagicMock()
        mock_chrome_cls.return_value = driver

        fetcher = CDEDataFetcher(headless=True)
        with self.assertRaises(Exception):
            fetcher.get_data_from_page("优先审评公示", "公示信息", page=1)

        driver.quit.assert_called_once()

    @patch("selenium.webdriver.Chrome")
    @patch("selenium.webdriver.ChromeOptions")
    def test_headless_option_is_set(self, mock_options_cls, mock_chrome_cls):
        options_mock = MagicMock()
        mock_options_cls.return_value = options_mock

        driver = MagicMock()
        driver.execute_script.return_value = False
        mock_chrome_cls.return_value = driver

        fetcher = CDEDataFetcher(headless=True)
        fetcher.get_data_from_page("优先审评公示", "公示信息", page=1)

        calls = [str(c) for c in options_mock.add_argument.call_args_list]
        self.assertTrue(any("headless" in c for c in calls))

    @patch("selenium.webdriver.Chrome")
    @patch("selenium.webdriver.ChromeOptions")
    def test_no_headless_option_when_false(self, mock_options_cls, mock_chrome_cls):
        options_mock = MagicMock()
        mock_options_cls.return_value = options_mock

        driver = MagicMock()
        driver.execute_script.return_value = False
        mock_chrome_cls.return_value = driver

        fetcher = CDEDataFetcher(headless=False)
        fetcher.get_data_from_page("优先审评公示", "公示信息", page=1)

        calls = [str(c) for c in options_mock.add_argument.call_args_list]
        self.assertFalse(any("headless" in c for c in calls))


if __name__ == "__main__":
    unittest.main()
