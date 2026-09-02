# myshop —— 测试金字塔演示项目

一个迷你网上商店,用来演示测试金字塔的四层。配套教程见上级目录的
`index.html`(总入口)与 `ai-workflow/` 下的 23 页 HTML。

> 分支说明:最新内容(含网页层与 E2E)在 `docs/windows-readme` 分支;
> `main` 受质量门禁保护,须走 PR 过「三道检查」后合并 —— 门禁本身就是教程第 19 页的教具。

## 快速开始

```bash
# macOS / Linux(在本项目根目录执行)
.venv/bin/python -m pytest
```

```powershell
# Windows PowerShell(在本项目根目录执行;虚拟环境不存在时先 python -m venv .venv)
.\.venv\Scripts\python.exe -m pytest
```

应该看到:

- **没装 playwright**:`17 passed, 1 skipped`(skip 的是 E2E,`importorskip` 生效)
- **装了 playwright + chromium**:`19 passed`(两条 E2E 真跑,见文末)

不确定自己属于哪种?跑一下就知道:

```powershell
.\.venv\Scripts\python.exe -m pip list | Select-String playwright
```

有 `playwright` 和 `pytest-playwright` 两行就是装了。

## 三条常用命令

```bash
# macOS / Linux
.venv/bin/python -m ruff check .     # 规范检查
.venv/bin/python -m mypy             # 类型检查
.venv/bin/python -m pytest           # 全量测试
```

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
```

本机实测耗时(Windows 11 + Python 3.12.10,2026-09-03):

| 命令 | 输出 | 耗时 |
|---|---|---|
| `ruff check .` | `All checks passed!` | 瞬间 |
| `mypy` | `Success: no issues found in 10 source files` | 约 1 秒 |
| `pytest`(不含 E2E) | `17 passed` | 3.86 秒 |
| `pytest`(含 E2E) | `19 passed` | 7.48 秒 |

> ⚠️ **一律写全路径**,`.venv/bin/python -m xxx`(Windows 是 `.\.venv\Scripts\python.exe -m xxx`)。
> Claude Code 在 Bash 里跑命令**不继承**你终端的 `activate` 状态,写全路径才可靠。
>
> 注意两边的目录名不一样:macOS/Linux 是 `.venv/bin/`,**Windows 是 `.venv\Scripts\`,
> 没有 `bin` 这个目录**。照抄上面 bash 那一栏在 Windows 上会「找不到文件」。

## 目录结构

```
myshop/
├── .venv/                       虚拟环境(不进 git)
├── pyproject.toml               pytest + mypy + ruff 三合一配置
├── .gitignore
├── .gitattributes               强制 LF 换行(见文末「换行符」)
├── myshop/                      源代码
│   ├── __init__.py
│   ├── price.py                 纯函数,不碰任何外部东西
│   ├── order.py                 跨模块调用 + 写 sqlite
│   ├── api.py                   HTTP 接口(只用标准库)
│   └── web.py                   最小下单网页(给第 4 层 E2E 点的)
└── tests/
    ├── test_price.py            ① 单元测试   5 条   0.01 秒
    ├── test_order.py            ② 集成测试   5 条   0.13 秒
    ├── test_api.py              ③ 接口测试   7 条   3.73 秒
    └── e2e/
        ├── conftest.py          自动起停服务器 + 数据库隔离
        └── test_checkout_e2e.py ④ E2E   2 条(没装浏览器驱动时 skip)
```

## 分层跑(流程步骤 3 用局部,步骤 5a 用全量)

```bash
# macOS / Linux
.venv/bin/python -m pytest tests/test_price.py     # 步骤 3:只跑改动相关的,快
.venv/bin/python -m pytest                         # 步骤 5a:提交前跑全量
```

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe -m pytest tests\test_price.py
.\.venv\Scripts\python.exe -m pytest
```

## 单独启动 API 试试

```bash
# macOS / Linux
PYTHONPATH=. .venv/bin/python -m myshop.api
```

```powershell
# Windows PowerShell —— 必须拆成两行
$env:PYTHONPATH = "."
.\.venv\Scripts\python.exe -m myshop.api
```

> PowerShell **没有** `VAR=值 命令` 这种行内前缀写法。照抄 bash 那一行不是「风格不对」,
> 是**解析错误**,敲下去直接报错。

另开一个终端:

```bash
# macOS / Linux
curl -X POST http://127.0.0.1:8000/orders \
  -H 'Content-Type: application/json' \
  -d '{"item":"咖啡","unit_cents":1250,"qty":2}'
```

```powershell
# Windows PowerShell —— charset=utf-8 不能省,原因见下
Invoke-RestMethod -Uri http://127.0.0.1:8000/orders -Method Post `
  -ContentType 'application/json; charset=utf-8' `
  -Body '{"item":"咖啡","unit_cents":1250,"qty":2}'
```

> Windows 上有**三个**坑叠在一起:
>
> 1. PowerShell 5.1 里的 `curl` 是 `Invoke-WebRequest` 的**别名**,不是真的 curl,
>    `-X` 会报参数绑定失败。想用真 curl 就写 `curl.exe`(Win10 1803 以后自带)。
> 2. 续行符是**反引号** `` ` ``,不是反斜杠 `\`。
> 3. **`charset=utf-8` 省掉的话,中文会被静默改坏。** PowerShell 5.1 不带 charset 时
>    按 latin-1 编 body,服务端收到的 `item` 会变成 `??` —— 而接口**照样返回 201 成功**,
>    你要查库才发现存错了。这正是本教程反复讲的那种失败:**不是报错,是悄悄给你错的结果。**
>    (另一种写法是把 body 显式转成字节:`-Body ([Text.Encoding]::UTF8.GetBytes($json))`,
>    效果一样。)

应该返回:

```json
{"id": 1, "item": "咖啡", "qty": 2, "total_cents": 2500, "total_text": "¥25.00"}
```

## 练习:亲手确认测试真的有效

「一条从来不会红的测试,等于没有这条测试。」自己验证一下:

1. 把 `myshop/price.py` 里的 `{fen:02d}` 改成 `{fen}`(去掉补零)
2. 跑 `pytest tests/test_price.py` → 应该有 3 条变红
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
# macOS / Linux
.venv/bin/python -m pip install pytest-playwright
.venv/bin/playwright install chromium
```

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe -m pip install pytest-playwright
.\.venv\Scripts\playwright.exe install chromium
```

装完再跑 `pytest`,那条 skip 就变成两条真跑的 E2E:`web.py` 提供最小下单页面,
`tests/e2e/conftest.py` 会自动起停服务器并把订单写进临时数据库(不污染项目目录)。

---

## Windows / 环境相关的三件事

这三条都是**本机跑得动、换台机器就未必**的那种问题,单独列出来。

### 1. 输出被捕获时的中文编码

直接在终端敲 `python -m myshop.api` 不会有事。但只要输出被**重定向或被工具捕获**
(`> log.txt`、`| tee`、编辑器的运行面板、Claude Code 代跑),Windows 的 stdout 会退回
系统代码页(英文机器 cp1252、简体中文机器 cp936),启动那句中文提示就会
`UnicodeEncodeError`,**服务器根本起不来**。

`api.py` 和 `web.py` 的入口已经加了保护,所以现在不会。但你自己写脚本时会撞上,
两个办法:

```powershell
$env:PYTHONUTF8 = "1"          # 最省事
```

或者在脚本入口加上和 `api.py` 里一样的那几行。

> 本机现状:`PYTHONIOENCODING=utf-8:surrogateescape` 已经在环境里设着,所以这个坑
> 在这台机器上**被挡住了**。别人的机器不一定有 —— 这正是「本机能跑不等于别人能跑」。

### 2. 代理:那 7 条接口测试靠 `NO_PROXY` 才不被劫走

`tests/test_api.py` 的 7 条走 `urllib`,而 `urllib` 会读 `HTTP_PROXY` / `HTTPS_PROXY`。
如果你机器上开了代理,必须让 `NO_PROXY` 里含 `127.0.0.1`,否则这 7 条会被劫进代理,
本机集体失败或挂起 —— **而云端 CI 永远是绿的**(runner 上没有代理)。

查一下:

```powershell
$env:NO_PROXY
```

看不到 `127.0.0.1` 就补上。

### 3. 换行符

仓库里加了 `.gitattributes`(`* text=auto eol=lf`),强制以 LF 入库和检出。
在此之前这件事靠的是本机 `git config core.autocrlf=false` —— 换台机器 clone,
如果那台是 `autocrlf=true`,整个仓库会变成 CRLF:对 Python 无害,但会造成整文件 diff。
