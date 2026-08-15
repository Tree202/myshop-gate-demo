"""第 4 层:E2E 测试(金字塔最顶上,数量最少、最慢、最容易「假失败」)。

这一层测什么:
    像真人一样开浏览器 -> 点按钮 -> 填表单 -> 看页面上有没有出现「下单成功」。
    只测最值钱的那一两条主流程(比如「能不能付钱」)。
这一层不测什么:
    不测价格进位、不测 404 文案、不测每种错误分支 ——
    那些用第 1~3 层测,又快又稳。E2E 写多了会慢到没人愿意跑。

⚠️ 本文件是示意代码,语法正确但默认不会真的执行:
   没装 playwright 时,下面的 importorskip 会让整个文件被 skip 掉,
   输出是干净的「1 skipped」而不是一屏 ImportError。

   想真跑请执行:
       .venv/bin/python -m pip install pytest-playwright
       .venv/bin/playwright install chromium
   并且先把商店的网页版跑起来(本示例项目只有 JSON 接口,没有页面)。
"""

import pytest

# importorskip:导入不到就跳过整个文件,而不是让测试报红
pytest.importorskip(
    "playwright.sync_api",
    reason="E2E 需要:pip install pytest-playwright && playwright install chromium",
)

# noqa: E402 是告诉 ruff:我知道 import 不在文件最顶上,这里是故意的
from playwright.sync_api import Page, expect, sync_playwright  # noqa: E402

首页 = "http://127.0.0.1:8000"


def test_用户可以从首页一路下单成功(page: Page) -> None:
    """写法一:用 pytest-playwright 提供的 page fixture(推荐,最省事)。"""
    page.goto(首页)

    # 按「用户看得见的东西」定位,而不是按 CSS class ——
    # class 改个名测试就挂了,按钮上的字改了才是真的改了功能
    page.get_by_role("link", name="咖啡").click()
    page.get_by_label("数量").fill("2")
    page.get_by_role("button", name="加入购物车").click()
    page.get_by_role("button", name="去结算").click()

    # expect(...) 会自动重试等待,不需要自己写 sleep
    expect(page.get_by_test_id("order-total")).to_have_text("¥25.00")
    expect(page.get_by_text("下单成功")).to_be_visible()


def test_不装_pytest_playwright_时的原始写法() -> None:
    """写法二:不用 fixture,自己开浏览器再关掉。看清楚流程用。"""
    with sync_playwright() as p:
        浏览器 = p.chromium.launch(headless=True)  # headless=False 可以看见窗口
        页面 = 浏览器.new_page()

        页面.goto(首页)
        页面.get_by_role("link", name="咖啡").click()
        页面.get_by_label("数量").fill("2")
        页面.get_by_role("button", name="加入购物车").click()
        页面.get_by_role("button", name="去结算").click()

        expect(页面.get_by_text("下单成功")).to_be_visible()

        浏览器.close()
