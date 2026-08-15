# myshop —— 测试金字塔演示项目

一个迷你网上商店,用来演示测试金字塔的四层。配套教程见上一级目录的
`claude-code-sop.html` 等四份 HTML。

## 快速开始

```bash
cd ~/Desktop/claude_data/learn_claude/myshop
.venv/bin/python -m pytest
```

应该看到 `17 passed, 1 skipped`(skipped 的是 E2E,需要装 playwright)。

## 三条常用命令

```bash
.venv/bin/python -m ruff check .     # 规范检查   0.02 秒
.venv/bin/python -m mypy             # 类型检查   0.27 秒
.venv/bin/python -m pytest           # 全量测试   3.66 秒
```

> ⚠️ 一律用 `.venv/bin/python -m xxx` 的形式。
> Claude Code 在 Bash 里跑命令不继承你终端的 `activate` 状态,写全路径才可靠。

## 目录结构

```
myshop/
├── .venv/                       虚拟环境(不进 git)
├── pyproject.toml               pytest + mypy + ruff 三合一配置
├── .gitignore
├── myshop/                      源代码
│   ├── __init__.py
│   ├── price.py                 纯函数,不碰任何外部东西
│   ├── order.py                 跨模块调用 + 写 sqlite
│   └── api.py                   HTTP 接口(只用标准库)
└── tests/
    ├── test_price.py            ① 单元测试   5 条   0.00 秒
    ├── test_order.py            ② 集成测试   5 条   0.02 秒
    ├── test_api.py              ③ 接口测试   7 条   3.64 秒
    └── e2e/
        └── test_checkout_e2e.py ④ E2E(示意,默认 skip)
```

## 分层跑(流程步骤 3 用局部,步骤 5a 用全量)

```bash
# 步骤 3:只跑改动相关的,快
.venv/bin/python -m pytest tests/test_price.py

# 步骤 5a:提交前跑全量,确认没弄坏别人
.venv/bin/python -m pytest
```

## 单独启动 API 试试

```bash
PYTHONPATH=. .venv/bin/python -m myshop.api
```

另开一个终端:

```bash
curl -X POST http://127.0.0.1:8000/orders \
  -H 'Content-Type: application/json' \
  -d '{"item":"咖啡","unit_cents":1250,"qty":2}'
```

应该返回:

```json
{"id": 1, "item": "咖啡", "qty": 2, "total_cents": 2500, "total_text": "¥25.00"}
```

## 练习:亲手确认测试真的有效

「一条从来不会红的测试,等于没有这条测试。」自己验证一下:

1. 把 `myshop/price.py` 里的 `{fen:02d}` 改成 `{fen}`(去掉补零)
2. 跑 `.venv/bin/python -m pytest tests/test_price.py` → 应该有 3 条变红
3. `git checkout -- .` 还原

更狠的一个:

1. 把 `order.py` 里 `total_text = format_price(total_cents)` 那一行挪到 `INSERT` **之后**
2. 再把 `if unit_cents < 0: raise ...` 删掉
3. 跑 `mypy` → **Success,它完全看不出来**
4. 跑 `pytest tests/test_order.py` → `test_单价为负数也要被拦下来并且不写库` 变红,
   而且失败原因是「库里查到了一条 -100 的脏数据」
5. `git checkout -- .` 还原

## E2E 想真跑的话

```bash
.venv/bin/python -m pip install pytest-playwright
.venv/bin/playwright install chromium
```

注意本项目只有 JSON 接口、没有网页,所以 E2E 是示意代码,真跑需要先做个页面。
