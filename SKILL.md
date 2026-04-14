---
name: cde-monitor
description: 查询中国药品审评中心（CDE）公示数据，包括优先审评、突破性治疗、受理品种、沟通交流等信息
version: 1.0.0
metadata:
  openclaw:
    emoji: 💊
    homepage: https://www.cde.org.cn
    requires:
      bins:
        - python3
        - google-chrome
    install:
      - pip: python/requirements.txt
    os:
      - linux
      - macos
---

# CDE Monitor — 中国药品审评中心数据查询 SKILL

本 SKILL 通过 Selenium 浏览器自动化技术抓取 [CDE（国家药品审评中心）](https://www.cde.org.cn) 网站的公示数据，支持优先审评、突破性治疗、受理品种目录、沟通交流公示等各类药品审评信息查询。

## 调用时机

当用户询问以下类型的问题时，使用本 SKILL：

- 查询 **优先审评** 相关信息：拟优先审评品种公示、纳入优先审评品种名单、异议论证结果
- 查询 **突破性治疗** 相关信息：拟突破性治疗品种、纳入突破性治疗品种名单、异议论证结果
- 查询 **新药受理** 相关信息：受理品种目录、在审品种目录
- 查询 **沟通交流公示** 信息
- 查询 CDE 网站任意左侧菜单 + 右侧 tab 组合的公示数据

## 安装依赖

```bash
pip install -r python/requirements.txt
```

> 本 SKILL 需要本地已安装 Google Chrome 浏览器，并能通过 `google-chrome` 或 `chromedriver` 调用。

## 使用方法

### 通用查询（推荐）

```python
from python.cde_monitor import CDEDataFetcher

fetcher = CDEDataFetcher(headless=True)

# 查询任意菜单 + tab 组合
data = fetcher.get_data_from_page(
    left_tab="沟通交流公示",   # 左侧菜单名称
    right_top_tab="公示信息",  # 右侧 tab 名称（可选）
    page=1                     # 页码，从 1 开始
)
```

### 快捷方法

| 方法 | 说明 |
|------|------|
| `get_priority_announcement(page)` | 拟优先审评品种公示 |
| `get_priority_approved_list(page)` | 纳入优先审评品种名单 |
| `get_priority_dissent_results(page)` | 优先审评异议论证结果查询 |
| `get_breakthrough_therapy_announcement(page)` | 拟突破性治疗品种 |
| `get_breakthrough_therapy_list(page)` | 纳入突破性治疗品种名单 |
| `get_breakthrough_therapy_dissent_results(page)` | 突破性治疗异议论证结果查询 |
| `get_new_drug_acceptance_announcement(page)` | 受理品种目录浏览 |
| `get_new_drug_approving_info(page)` | 在审品种目录浏览 |
| `get_communication_notice(page)` | 沟通交流公示信息 |

### 保存结果

```python
records = data.get("data", {}).get("records", [])

# 保存为 Excel
fetcher.save_to_excel(records, "output.xlsx")

# 保存为 JSON
fetcher.save_to_json(records, "output.json")
```

## 返回数据格式

成功时返回如下格式的字典：

```json
{
  "code": 200,
  "data": {
    "total": 100,
    "records": [
      {
        "acceptid": "受理号",
        "drgnamecn": "药品名称（中文）",
        "company": "申请人/企业名称",
        ...
      }
    ]
  }
}
```

## 可用的左侧菜单（`left_tab`）

- `受理品种信息` — 受理品种目录浏览、在审品种目录浏览
- `审评任务公示`
- `沟通交流公示` — 政策信息、公示信息、常见一般性技术问题
- `优先审评公示` — 拟优先审评品种公示、纳入优先审评品种名单、异议论证结果查询
- `突破性治疗公示` — 拟突破性治疗品种、纳入突破性治疗品种名单、异议论证结果查询
- `共性问题`
- `临床试验默示许可`
- `上市药品信息`
- `原辅包登记信息`
- `药品目录集信息`
- `重点工作`
- `附条件批准品种`
- `其他公开信息`

## 示例：查询"沟通交流公示"的第 1 页数据

```python
from python.cde_monitor import CDEDataFetcher

fetcher = CDEDataFetcher(headless=True)
data = fetcher.get_communication_notice(page=1)

if data and data.get("code") == 200:
    records = data["data"]["records"]
    total = data["data"]["total"]
    print(f"共 {total} 条记录，当前页 {len(records)} 条")
    for r in records[:5]:
        print(r)
```

## 注意事项

- 本工具通过浏览器自动化方式访问 CDE 网站，受网络环境影响，偶尔可能超时或返回空数据，重试即可。
- CDE 网站使用了 JavaScript 加密参数，直接调用接口较为困难，因此采用浏览器性能日志捕获 API 响应的方案。
- `headless=True` 适合自动化/服务器环境；本地调试可设为 `headless=False` 以查看浏览器操作过程。
