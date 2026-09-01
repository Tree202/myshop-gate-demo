"""E2E 专用的夹具:在测试开始前把商店跑起来,结束后关掉。

为什么放在 tests/e2e/conftest.py 而不是根目录的 conftest:
    这样它只对 E2E 那一层生效。第 1~3 层不需要服务器,
    也不该为了跑一条单元测试就白白起一个 HTTP 服务。

为什么用 daemon 线程:
    HTTPServer.serve_forever() 会一直阻塞。放进 daemon 线程里,
    万一测试异常退出,这个线程不会把 pytest 卡住不放。
"""

import threading
from collections.abc import Iterator

import pytest

from myshop.order import init_db
from myshop.web import make_web_server

端口 = 8000


@pytest.fixture(scope="session", autouse=True)
def 商店服务器() -> Iterator[str]:
    """整个 E2E 会话共用一个服务器,起一次、关一次。"""
    init_db()  # 建表。不建的话第一次下单会 no such table
    try:
        服务器 = make_web_server(端口)
    except OSError as exc:  # pragma: no cover - 只在端口被占时走到
        pytest.fail(
            f"起不了 127.0.0.1:{端口} —— {exc}。"
            f"多半是别的程序占了这个端口,关掉它再跑。"
        )
    线程 = threading.Thread(target=服务器.serve_forever, daemon=True)
    线程.start()
    try:
        yield f"http://127.0.0.1:{端口}"
    finally:
        服务器.shutdown()
        服务器.server_close()
        线程.join(timeout=5)
