"""E2E 专用的夹具:在测试开始前把商店跑起来,结束后关掉。

为什么放在 tests/e2e/conftest.py 而不是根目录的 conftest:
    这样它只对 E2E 那一层生效。第 1~3 层不需要服务器,
    也不该为了跑一条单元测试就白白起一个 HTTP 服务。

为什么用 daemon 线程:
    HTTPServer.serve_forever() 会一直阻塞。放进 daemon 线程里,
    万一测试异常退出,这个线程不会把 pytest 卡住不放。

为什么要换数据库路径:
    不换的话,E2E 每跑一次就往项目根目录的 myshop.db 里追加一条订单 ——
    共享状态无界增长,正是第 10 页讲的 E2E 抖动温床。
    做法和第 3 层一样:monkeypatch 掉 order.DB_PATH,指到一次性临时目录。
"""

import threading
from collections.abc import Iterator

import pytest

from myshop import order
from myshop.order import init_db
from myshop.web import make_web_server

端口 = 8000


@pytest.fixture(scope="session", autouse=True)
def 商店服务器(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """整个 E2E 会话共用一个服务器,起一次、关一次。

    yield 出来的是首页地址 —— 测试要用它,别自己写死一份:
    端口只在这个文件里出现一次,才谈得上「唯一事实源」。
    """
    # 数据库隔离:E2E 的订单写进临时目录,跑完由 pytest 自动清理
    mp = pytest.MonkeyPatch()
    mp.setattr(order, "DB_PATH", str(tmp_path_factory.mktemp("e2e") / "e2e.db"))
    init_db()  # 建表。不建的话第一次下单会 no such table

    try:
        服务器 = make_web_server(端口)
    except OSError as exc:  # pragma: no cover - 只在端口被占时走到
        mp.undo()
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
        mp.undo()
