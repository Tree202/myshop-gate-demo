"""第 3 层:接口测试(API 测试)。

这一层测什么:
    真的启动一个 HTTP 服务器,真的用 urllib 发请求进去,
    检查状态码(201 / 400 / 404)、返回的 JSON 结构。
    也就是「契约」:别人按文档调你的接口,拿到的东西对不对。
这一层不测什么:
    不测浏览器、不测页面长什么样(那是第 4 层 E2E 的活)。
    也不再重复测价格进位这种细节(第 1 层已经测过了)。
"""

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple

import pytest

from myshop import api, order


@pytest.fixture()
def 服务器(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """启动一个真的 HTTP 服务器,测完自动关掉。返回它的地址。"""
    # 让接口层写到临时数据库,别碰真实的 myshop.db
    monkeypatch.setattr(order, "DB_PATH", str(tmp_path / "api.db"))

    服务 = api.make_server(port=0)  # 0 = 让系统分配空闲端口,避免端口冲突
    # daemon=True:主进程结束时这个线程不会拖住不放
    线程 = threading.Thread(target=服务.serve_forever, daemon=True)
    线程.start()

    yield f"http://127.0.0.1:{服务.server_port}"

    # yield 之后的代码是「收尾」,不管测试成功失败都会执行
    服务.shutdown()
    服务.server_close()
    线程.join(timeout=5)


def 发请求(
    url: str,
    method: str,
    payload: Any = None,
    raw_body: Optional[bytes] = None,
) -> Tuple[int, Dict[str, Any]]:
    """一个小助手:发一个 HTTP 请求,返回 (状态码, 解析好的 JSON)。

    raw_body 用来发「故意不合法的 JSON」,测服务器的容错。
    """
    if raw_body is not None:
        data = raw_body
    elif payload is not None:
        data = json.dumps(payload).encode("utf-8")
    else:
        data = None

    请求 = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(请求) as 响应:
            return 响应.status, json.loads(响应.read())
    except urllib.error.HTTPError as 错误:
        # 4xx/5xx 在 urllib 里是以异常形式抛出来的,要接住才能断言状态码
        return 错误.code, json.loads(错误.read())


def test_下单接口返回_201_和订单内容(服务器: str) -> None:
    状态码, 数据 = 发请求(
        f"{服务器}/orders",
        "POST",
        {"item": "咖啡", "unit_cents": 1250, "qty": 2},
    )

    assert 状态码 == 201  # 201 Created:新建资源成功
    assert 数据["item"] == "咖啡"
    assert 数据["total_cents"] == 2500
    assert 数据["total_text"] == "¥25.00"
    assert 数据["id"] >= 1


def test_下单之后能用_GET_查回来(服务器: str) -> None:
    _, 新订单 = 发请求(
        f"{服务器}/orders",
        "POST",
        {"item": "键盘", "unit_cents": 39900, "qty": 1},
    )

    状态码, 数据 = 发请求(f"{服务器}/orders/{新订单['id']}", "GET")

    assert 状态码 == 200
    assert 数据["item"] == "键盘"
    assert 数据["total_text"] == "¥399.00"


def test_缺字段要返回_400(服务器: str) -> None:
    状态码, 数据 = 发请求(f"{服务器}/orders", "POST", {"item": "咖啡"})

    assert 状态码 == 400
    assert "error" in 数据


def test_数量为零要返回_400(服务器: str) -> None:
    状态码, _ = 发请求(
        f"{服务器}/orders",
        "POST",
        {"item": "咖啡", "unit_cents": 1250, "qty": 0},
    )

    assert 状态码 == 400


def test_单价为负要返回_400(服务器: str) -> None:
    状态码, _ = 发请求(
        f"{服务器}/orders",
        "POST",
        {"item": "咖啡", "unit_cents": -1, "qty": 1},
    )

    assert 状态码 == 400


def test_请求体不是合法_JSON_要返回_400_而不是_500(服务器: str) -> None:
    """这条测的是「解析 JSON 放在 try 里面还是外面」这个容易写错的地方。

    如果 json.loads 写在 try 外面,一个畸形请求会让服务器抛未捕获异常,
    客户端拿到 500(服务器内部错误),终端还会打一屏 traceback。
    正确的行为是老老实实返回 400(是你请求发错了,不是我崩了)。
    """
    # 注意:字节串字面量 b"..." 里只能放 ASCII 字符,
    # 想发中文得先写成普通字符串再 .encode("utf-8")
    畸形请求体 = "{这不是合法的 JSON".encode("utf-8")

    状态码, 数据 = 发请求(f"{服务器}/orders", "POST", raw_body=畸形请求体)

    assert 状态码 == 400
    assert "error" in 数据


def test_查不存在的订单要返回_404(服务器: str) -> None:
    状态码, 数据 = 发请求(f"{服务器}/orders/99999", "GET")

    assert 状态码 == 404
    assert "不存在" in 数据["error"]
