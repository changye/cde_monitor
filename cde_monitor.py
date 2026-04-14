"""
CDE (中国药品审评中心) 数据获取工具

该模块通过 Selenium 浏览器自动化技术获取 CDE 网站的药品审评数据。
由于 CDE 网站使用了加密的 API 参数，直接调用接口较为困难，
因此采用浏览器自动化方案，通过捕获页面的网络请求来获取数据。

使用方法：
    from utils.cde_new_drug import CDEDataFetcher
    
    # 创建获取器
    fetcher = CDEDataFetcher(headless=True)
    
    # ========== 通用方法（推荐）==========
    # 获取任意页面数据
    data = fetcher.get_data_from_page(
        left_tab="沟通交流公示",      # 左侧菜单名称
        right_top_tab="公示信息",     # 右侧顶部tab名称
        page=1                        # 页码
    )
    
    # ========== 快捷方法（优先审评专用）==========
    # 获取"拟优先审评品种公示"数据
    data1 = fetcher.get_priority_announcement(page=1)
    
    # 获取"纳入优先审评品种名单"数据
    data2 = fetcher.get_priority_approved_list(page=1)
    
    # 获取"异议论证结果查询"数据
    data3 = fetcher.get_dissent_results(page=1)

左侧菜单示例：
    - 受理品种信息、审评任务公示、沟通交流公示、优先审评公示
    - 突破性治疗公示、共性问题、临床试验默示许可、上市药品信息
    - 原辅包登记信息、药品目录集信息、重点工作、附条件批准品种、其他公开信息

右侧Tab示例（因左侧菜单不同而异）：
    - 沟通交流公示: 政策信息、公示信息、常见一般性技术问题
    - 优先审评公示: 拟优先审评品种公示、纳入优先审评品种名单、异议论证结果查询

依赖：
    - selenium >= 4.0.0
    - pandas
    - openpyxl
"""

import json
import time
from typing import Dict, List, Optional


class CDEDataFetcher:
    """
    CDE 数据获取器
    
    通过 Selenium 浏览器自动化技术获取 CDE 网站数据
    自动捕获浏览器的网络请求，绕过加密参数的问题
    """
    
    def __init__(self, headless: bool = False):
        """
        初始化获取器
        
        Args:
            headless: 是否使用无头模式（不显示浏览器窗口），默认为 False
        """
        self.base_url = "https://www.cde.org.cn"
        self.headless = headless
    
    def get_data_from_page(self, left_tab: str, right_top_tab: str = None, page: int = 1) -> Optional[Dict]:
        """
        通用方法：从CDE网站获取指定页面的数据
        
        Args:
            left_tab: 左侧菜单名称，如 "优先审评公示"、"沟通交流公示" 等
            right_top_tab: 右侧顶部tab名称，如 "公示信息"、"纳入优先审评品种名单" 等
                          如果该菜单只有一个tab或不需要切换tab，可以传None
            page: 页码，从 1 开始
            
        Returns:
            API 响应数据字典，包含 records 列表
            
        Examples:
            # 获取沟通交流公示的公示信息
            data = fetcher.get_data_from_page("沟通交流公示", "公示信息", page=1)
            
            # 获取优先审评公示的纳入名单
            data = fetcher.get_data_from_page("优先审评公示", "纳入优先审评品种名单", page=2)
        """
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        driver = webdriver.Chrome(options=options)
        
        try:
            # 步骤1: 访问信息公开页面
            url = f"{self.base_url}/main/xxgk/listpage/9f9c74c73e0f8f56a8bfbc646055026d"
            print(f"  步骤1: 访问信息公开页面...")
            driver.get(url)
            time.sleep(8)
            
            # 步骤2: 点击左侧菜单
            print(f"  步骤2: 点击左侧'{left_tab}'菜单...")
            js_click_menu = f"""
            var links = document.querySelectorAll('a');
            for (var i = 0; i < links.length; i++) {{
                if (links[i].textContent.trim() === '{left_tab}') {{
                    links[i].click();
                    return true;
                }}
            }}
            return false;
            """
            result = driver.execute_script(js_click_menu)
            
            if result:
                print(f"  ✓ 已点击'{left_tab}'菜单")
                time.sleep(5)
            else:
                print(f"  ✗ 未找到'{left_tab}'菜单")
                return None
            
            # 步骤3: 点击右侧顶部tab（如果指定了）
            if right_top_tab:
                print(f"  步骤3: 切换到tab '{right_top_tab}'...")
                
                js_click_tab = f"""
                var targetText = '{right_top_tab}';
                
                // 方法1: 精确匹配span文本
                var spans = document.querySelectorAll('span');
                for (var i = 0; i < spans.length; i++) {{
                    var text = spans[i].textContent.trim();
                    if (text === targetText) {{
                        spans[i].click();
                        return 'clicked span: ' + text;
                    }}
                }}
                
                // 方法2: 查找所有可点击元素
                var clickables = document.querySelectorAll('a, div, li');
                for (var i = 0; i < clickables.length; i++) {{
                    var elem = clickables[i];
                    var text = elem.textContent.trim();
                    // 避免点击左侧菜单
                    var isLeftMenu = elem.closest('.left-nav, .sidebar, .menu-list, .el-menu, [class*="left"]');
                    if (!isLeftMenu && text === targetText) {{
                        elem.click();
                        return 'clicked element: ' + text;
                    }}
                }}
                
                return null;
                """
                clicked_result = driver.execute_script(js_click_tab)
                
                if clicked_result:
                    print(f"  ✓ {clicked_result}")
                    time.sleep(5)
                else:
                    print(f"  ✗ 未找到tab '{right_top_tab}'")
                # 清除左侧菜单加载时产生的日志，确保后续只捕获右侧tab对应的API响应
                driver.get_log('performance')
            else:
                print(f"  步骤3: 无需切换tab")
                time.sleep(3)
                # 清除之前的日志
                driver.get_log('performance')
            
            # 步骤4: 处理分页（如果需要）
            if page > 1:
                print(f"  步骤4: 切换到第 {page} 页...")
                
                
                try:
                    # 先检查总页数
                    check_pages_js = """
                    var totalSpan = document.querySelector('.layui-laypage-count');
                    if (totalSpan) {
                        var match = totalSpan.textContent.match(/共\\s*(\\d+)\\s*条/);
                        if (match) {
                            return {total: parseInt(match[1]), pageSize: 10};
                        }
                    }
                    var pageButtons = document.querySelectorAll('.layui-laypage a');
                    var maxPage = 1;
                    for (var i = 0; i < pageButtons.length; i++) {
                        var num = parseInt(pageButtons[i].textContent);
                        if (!isNaN(num) && num > maxPage) maxPage = num;
                    }
                    return {maxPage: maxPage};
                    """
                    page_info = driver.execute_script(check_pages_js)
                    
                    if page_info:
                        total = page_info.get('total', 0)
                        page_size = page_info.get('pageSize', 10)
                        max_page = page_info.get('maxPage', 1)
                        
                        if total > 0:
                            max_page = (total + page_size - 1) // page_size
                        
                        if page > max_page:
                            print(f"  ✗ 页码 {page} 超出范围（最大 {max_page} 页）")
                            return None
                        
                        print(f"    (总记录: {total}, 最大页数: {max_page})")
                    
                    # 填写页码
                    goto_page_js = f"""
                    var input = null;
                    var skipDiv = document.querySelector('.layui-laypage-skip');
                    if (skipDiv) {{
                        input = skipDiv.querySelector('input.layui-input');
                    }}
                    if (!input) {{
                        var inputs = document.querySelectorAll('input.layui-input');
                        for (var i = 0; i < inputs.length; i++) {{
                            var parent = inputs[i].parentElement;
                            if (parent && parent.textContent.includes('到第') && parent.textContent.includes('页')) {{
                                input = inputs[i];
                                break;
                            }}
                        }}
                    }}
                    if (input) {{
                        input.value = '';
                        input.focus();
                        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        nativeInputValueSetter.call(input, '{page}');
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return 'input_filled';
                    }}
                    return null;
                    """
                    input_result = driver.execute_script(goto_page_js)
                    
                    if input_result:
                        time.sleep(0.5)
                        
                        # 点击确定按钮
                        click_confirm_js = """
                        var btn = document.querySelector('.layui-laypage-btn');
                        if (btn) {
                            btn.click();
                            return 'clicked_confirm';
                        }
                        return null;
                        """
                        confirm_result = driver.execute_script(click_confirm_js)
                        
                        if confirm_result:
                            print(f"  ✓ 已切换到第 {page} 页")
                            time.sleep(5)
                        else:
                            print(f"  ✗ 未找到确定按钮")
                    else:
                        print(f"  ✗ 未找到页码输入框")
                        
                except Exception as e:
                    print(f"  切换页码时出错: {e}")
            
            # 步骤5: 获取数据
            step_num = 5 if page > 1 else 4
            print(f"  步骤{step_num}: 获取API数据...")
            time.sleep(3)
            
            # 获取性能日志
            logs = driver.get_log('performance')
            
            for log in reversed(logs):
                try:
                    message = json.loads(log['message'])
                    method = message.get('message', {}).get('method', '')
                    
                    if 'Network.responseReceived' in method:
                        params = message.get('message', {}).get('params', {})
                        response = params.get('response', {})
                        url_in_log = response.get('url', '')
                        
                        # 查找CDE API响应 - 扩展关键字匹配
                        api_keywords = ['getMenuListHc', 'priorityList', 'priority', 'xxgk', 
                                       'getList', 'list', 'query', 'search', 'page']
                        if ('cde.org.cn' in url_in_log and 
                            any(keyword.lower() in url_in_log.lower() for keyword in api_keywords)):
                            request_id = params.get('requestId')
                            if request_id:
                                try:
                                    response_body = driver.execute_cdp_cmd(
                                        'Network.getResponseBody', 
                                        {'requestId': request_id}
                                    )
                                    body = response_body.get('body', '')
                                    data = json.loads(body)
                                    
                                    if isinstance(data, dict) and data.get('code') == 200:
                                        if data.get('data', {}).get('records'):
                                            print(f"  ✓ 成功获取API响应 (URL: ...{url_in_log[-50:]})")
                                            return data
                                except Exception:
                                    pass
                except Exception:
                    continue
            
            print(f"  ✗ 未找到有效的API响应")
            return None
            
        finally:
            driver.quit()



    # 新药上市受理公示信息查询
    def get_new_drug_acceptance_announcement(self, page: int = 1) -> Optional[Dict]:
        """
        获取"受理品种目录浏览"列表（快捷方法）
        
        Args:
            page: 页码，从 1 开始
            
        Returns:
            API 响应数据字典
        """
        return self.get_data_from_page("受理品种信息", "受理品种目录浏览", page)
    
    # 在审品种目录浏览
    def get_new_drug_approving_info(self, page: int = 1) -> Optional[Dict]:
        """
        获取"在审品种目录浏览"列表（快捷方法）
        
        Args:
            page: 页码，从 1 开始
            
        Returns:
            API 响应数据字典
        """
        return self.get_data_from_page("受理品种信息", "在审品种目录浏览", page)
    
    # 优先审评公示快捷方法
    def get_priority_announcement(self, page: int = 1) -> Optional[Dict]:
        """
        获取"拟优先审评品种公示"列表（快捷方法）
        
        Args:
            page: 页码，从 1 开始
            
        Returns:
            API 响应数据字典
        """
        return self.get_data_from_page("优先审评公示", "拟优先审评品种公示", page)
    
    def get_priority_approved_list(self, page: int = 1) -> Optional[Dict]:
        """
        获取"纳入优先审评品种名单"列表（快捷方法）
        
        Args:
            page: 页码，从 1 开始
            
        Returns:
            API 响应数据字典
        """
        return self.get_data_from_page("优先审评公示", "纳入优先审评品种名单", page)
    
    def get_priority_dissent_results(self, page: int = 1) -> Optional[Dict]:
        """
        获取"异议论证结果查询"列表（快捷方法）
        
        Args:
            page: 页码，从 1 开始
            
        Returns:
            API 响应数据字典
        """
        return self.get_data_from_page("优先审评公示", "异议论证结果查询", page)
    
    # 突破性治疗公示
    def get_breakthrough_therapy_announcement(self, page: int = 1) -> Optional[Dict]:
        """
        获取"突破性治疗公示"的"公示信息"列表（快捷方法）
        
        Args:
            page: 页码，从 1 开始
            
        Returns:
            API 响应数据字典
        """
        return self.get_data_from_page("突破性治疗公示", "拟突破性治疗品种", page)
    
    def get_breakthrough_therapy_list(self, page: int = 1) -> Optional[Dict]:
        """
        获取"突破性治疗公示"的"纳入突破性治疗品种名单"列表（快捷方法）
        
        Args:
            page: 页码，从 1 开始
            
        Returns:
            API 响应数据字典
        """
        return self.get_data_from_page("突破性治疗公示", "纳入突破性治疗品种名单", page)
    
    def get_breakthrough_therapy_dissent_results(self, page: int = 1) -> Optional[Dict]:
        """
        获取"突破性治疗公示"的"异议论证结果查询"列表（快捷方法）
        
        Args:
            page: 页码，从 1 开始
            
        Returns:
            API 响应数据字典
        """
        return self.get_data_from_page("突破性治疗公示", "异议论证结果查询", page)
    

    # 沟通交流公示快捷方法
    def get_communication_notice(self, page: int = 1) -> Optional[Dict]:
        """
        获取"沟通交流公示"的"公示信息"列表（快捷方法）
        
        Args:
            page: 页码，从 1 开始
            
        Returns:
            API 响应数据字典
        """
        return self.get_data_from_page("沟通交流公示", "公示信息", page)
      
    def save_to_excel(self, records: List[Dict], filename: str = 'cde_data.xlsx') -> None:
        """
        保存数据到 Excel 文件
        
        Args:
            records: 记录列表
            filename: 输出文件名，默认为 'cde_data.xlsx'
        """
        import pandas as pd
        
        if not records:
            print("没有数据可保存")
            return
        
        df = pd.DataFrame(records)
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"✓ 数据已保存到: {filename}")
    
    def save_to_json(self, records: List[Dict], filename: str = 'cde_data.json') -> None:
        """
        保存数据到 JSON 文件
        
        Args:
            records: 记录列表
            filename: 输出文件名，默认为 'cde_data.json'
        """
        if not records:
            print("没有数据可保存")
            return
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        print(f"✓ 数据已保存到: {filename}")


if __name__ == "__main__":
    # 使用示例
    print("=" * 80)
    print("CDE 数据获取工具 - 通用版")
    print("=" * 80)
    
    fetcher = CDEDataFetcher(headless=False)
    
    # 示例1: 使用通用函数获取"沟通交流公示"的"公示信息"
    print("\n【示例1】通用函数: 沟通交流公示 -> 公示信息 (第1页)")
    data1 = fetcher.get_data_from_page(
        left_tab="沟通交流公示",
        right_top_tab="公示信息",
        page=1
    )
    
    if data1 and data1.get('code') == 200:
        records1 = data1.get('data', {}).get('records', [])
        total = data1.get('data', {}).get('total', 0)
        print(f"✓ 成功! 总记录: {total}, 当前页: {len(records1)}条")
        if records1:
            print(f"  字段: {list(records1[0].keys())[:6]}...")
            # 打印前三条记录的简要信息
            for i, r in enumerate(records1[:3], 1):
                print(f"  第{i}条: 申请编号={r.get('subcode', 'N/A')}, 单位={r.get('companyName', 'N/A')[:20] if r.get('companyName') else 'N/A'}")
    else:
        print("✗ 获取失败")
    
    print("\n" + "-" * 80)
    
    # 示例2: 使用快捷方法获取"纳入优先审评品种名单"
    print("\n【示例2】快捷方法: 纳入优先审评品种名单 (第2页)")
    data2 = fetcher.get_priority_approved_list(page=2)
    
    if data2 and data2.get('code') == 200:
        records2 = data2.get('data', {}).get('records', [])
        total = data2.get('data', {}).get('total', 0)
        print(f"✓ 成功! 总记录: {total}, 当前页: {len(records2)}条")
        if records2:
            print(f"  字段: {list(records2[0].keys())[:6]}...")
            # 打印前三条记录的简要信息
            for i, r in enumerate(records2[:3], 1):
                print(f"  第{i}条: 受理号={r.get('acceptid', 'N/A')}, 药品名称={r.get('drgnamecn', 'N/A')}, 企业名称={r.get('company', 'N/A')[:20] if r.get('company') else 'N/A'}")
    else:
        print("✗ 获取失败")

    # 示例3： "突破性治疗公示" 的 "拟突破性治疗品种"
    print("\n" + "-" * 80)
    data3 = fetcher.get_breakthrough_therapy_announcement(page=1)
    print("\n【示例3】快捷方法: 突破性治疗公示 -> 拟突破性治疗品种 (第1页)")
    if data3 and data3.get('code') == 200:
        records3 = data3.get('data', {}).get('records', [])
        total = data3.get('data', {}).get('total', 0)
        print(f"✓ 成功! 总记录: {total}, 当前页: {len(records3)}条")
        if records3:
            print(f"  字段: {list(records3[0].keys())[:6]}...")
            for i, r in enumerate(records3[:3], 1):
                print(f"  第{i}条: 受理号={r.get('acceptid', 'N/A')}, 药品名称={r.get('drgnamecn', 'N/A')}, 企业名称={r.get('company', 'N/A')[:20] if r.get('company') else 'N/A'}")
    else:
        print("✗ 获取失败")

    # 示例4： 使用通用函数获取"受理品种目录浏览"
    print("\n" + "-" * 80)
    data4 = fetcher.get_new_drug_acceptance_announcement(page=1)
    print("\n【示例4】通用函数: 受理品种信息 -> 受理品种目录浏览 (第1页)")
    if data4 and data4.get('code') == 200:
        records4 = data4.get('data', {}).get('records', [])
        total = data4.get('data', {}).get('total', 0)
        print(f"✓ 成功! 总记录: {total}, 当前页: {len(records4)}条")
        if records4:
            print(f"  字段: {list(records4[0].keys())[:6]}...")
            for i, r in enumerate(records4[:3], 1):
                print(f"  第{i}条: 受理号={r.get('acceptid', 'N/A')}, 药品名称={r.get('drgnamecn', 'N/A')}, 企业名称={r.get('companys', 'N/A')[:20] if r.get('companys') else 'N/A'}")
    
    print("\n" + "=" * 80)
    print("使用说明：")
    print("  【通用方法】")
    print("  get_data_from_page(left_tab, right_top_tab, page)")
    print("    - left_tab: 左侧菜单名称 (如 '沟通交流公示', '优先审评公示')")
    print("    - right_top_tab: 右侧tab名称 (如 '公示信息', '纳入优先审评品种名单')")
    print("    - page: 页码")
    print()
    print("  【快捷方法】")
    print("  优先评审公示相关：")
    print("  - get_priority_announcement()    - 拟优先审评品种公示")
    print("  - get_priority_approved_list()   - 纳入优先审评品种名单")
    print("  - get_priority_dissent_results() - 优先审评异议论证结果查询")
    print("  突破性治疗公示相关：")
    print("  - get_breakthrough_therapy_announcement() - 突破性治疗公示 -> 拟突破性治疗品种")
    print("  - get_breakthrough_therapy_list()         - 突破性治疗公示 -> 纳入突破性治疗品种名单")
    print("  - get_breakthrough_therapy_dissent_results() - 突破性治疗异议论证结果查询")
    print("  受理品种信息相关：")
    print("  - get_new_drug_acceptance_announcement() - 新药上市受理公示信息查询")
    print("  - get_new_drug_approving_info()         - 在审品种目录浏览")
    print("  沟通交流公示相关：")
    print("  - get_communication_notice()     - 沟通交流公示信息")
    print("=" * 80)
