"""第 4 层:E2E 测试(金字塔最顶上,数量最少、最慢、最容易「假失败」)。

这一层测什么:
    像真人一样开浏览器 -> 点按钮 -> 填表单 -> 看页面上有没有出现「下单成功」。
    只测最值钱的那一两条主流程(比如「能不能付钱」)。
这一层不测什么:
    不测价格进位、不测 404 文案、不测每种错误分支 ——
    那些用第 1~3 层测,又快又稳。E2E 写多了会慢到没人愿意跑。

跑这一层需要两样东西(都已经装好):
    .venv/bin/python -m pip install pytest-playwright
    .venv/bin/playwright install chromium
页面由 myshop/web.py 提供,服务器在 conftest.py 里自动起停 ——
不用你手动开一个终端跑服务。
"""

import threading

import pytest

# importorskip:导入不到就跳过整个文件,而不是让测试报红。
# 装上之后这一行就不再跳过了,两条 E2E 会真的开浏览器跑。
pytest.importorskip(
    "playwright.sync_api",
    reason="E2E 需要:pip install pytest-playwright && playwright install chromium",
)

# noqa: E402 是告诉 ruff:我知道 import 不在文件最顶上,这里是故意的
from playwright.sync_api import Page, expect, sync_playwright  # noqa: E402

首页 = "http://127.0.0.1:8000"


def _走一遍下单流程(页面: Page) -> None:
    """两种写法共用的主流程 —— 定位方式一样,只是谁来提供浏览器不同。

    按「用户看得见的东西」定位,而不是按 CSS class ——
    class 改个名测试就挂了,按钮上的字改了才是真的改了功能。
    """
    页面.goto(首页)
    页面.get_by_role("link", name="咖啡").click()
    页面.get_by_label("数量").fill("2")
    页面.get_by_role("button", name="加入购物车").click()
    页面.get_by_role("button", name="去结算").click()

    # expect(...) 会自动重试等待,不需要自己写 sleep
    expect(页面.get_by_test_id("order-total")).to_have_text("¥25.00")
    expect(页面.get_by_text("下单成功")).to_be_visible()


def test_用户可以从首页一路下单成功(page: Page) -> None:
    """写法一:用 pytest-playwright 提供的 page fixture(推荐,最省事)。"""
    _走一遍下单流程(page)


def test_不装_pytest_playwright_时的原始写法() -> None:
    """写法二:不用 fixture,自己开浏览器再关掉。看清楚流程用。

    ⚠️ 为什么要套一层线程 —— 这是真跑起来才发现的坑:
        sync_playwright() 不能跑在「已经有事件循环在转」的线程里,
        而写法一用的 page fixture 恰好会在本线程留下一个。
        两条测试同进程时,写法一先跑,写法二就会报
        「Playwright Sync API inside the asyncio loop」;
        反过来先跑写法二,两条都过。

        也就是说:它俩谁先跑,结果不一样 ——
        这正是第 10 页讲的那种「测试之间互相影响」的抖动。
        靠调换顺序能糊过去,但那是把依赖藏起来,不是解决它。
        开一条干净线程,两条就都能跑,而且和顺序无关。
    """
    出错: list[BaseException] = []

    def 跑() -> None:
        try:
            with sync_playwright() as p:
                浏览器 = p.chromium.launch(headless=True)  # headless=False 可以看见窗口
                页面 = 浏览器.new_page()
                try:
                    _走一遍下单流程(页面)
                finally:
                    浏览器.close()
        except BaseException as exc:  # noqa: BLE001  子线程的异常要带回主线程
            出错.append(exc)

    线程 = threading.Thread(target=跑)
    线程.start()
    线程.join()

    # 子线程里的失败不会让主线程的测试变红,必须自己抛出来
    if 出错:
        raise 出错[0]
