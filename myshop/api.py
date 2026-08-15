"""HTTP 接口层:只用 Python 标准库,不用装任何第三方框架。

只有两个接口:
    POST /orders      下单,body 是 {"item": "咖啡", "unit_cents": 1250, "qty": 2}
    GET  /orders/<id> 查单

它自己不算钱、不写库,只负责「把 HTTP 翻译成函数调用,再把结果翻译回 JSON」。
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict

from myshop.order import create_order, get_order


class ShopHandler(BaseHTTPRequestHandler):
    """每来一个请求,http.server 就调用这里的 do_POST / do_GET。"""

    def do_POST(self) -> None:  # noqa: N802  (方法名是标准库规定的)
        if self.path != "/orders":
            self._send(404, {"error": "没有这个接口"})
            return

        # 请求体的长度写在 Content-Length 头里,要按这个长度去读
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"

        # 解析 JSON 必须放在 try 里面:客户端发来的东西不一定是合法 JSON。
        # 放在外面的话,一个畸形请求就会让服务器抛未捕获异常 -> 500 + 终端一屏红字,
        # 而设计上这应该是一个规规矩矩的 400。
        try:
            body: Dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            self._send(400, {"error": "请求体不是合法的 JSON"})
            return

        if not isinstance(body, dict):
            self._send(400, {"error": "请求体必须是一个 JSON 对象"})
            return

        try:
            order = create_order(
                item=str(body["item"]),
                unit_cents=int(body["unit_cents"]),
                qty=int(body["qty"]),
            )
        except KeyError as exc:
            self._send(400, {"error": f"缺少字段 {exc}"})
            return
        except (TypeError, ValueError) as exc:
            # ValueError 来自 create_order 的校验;TypeError 来自 int(None) 这类
            self._send(400, {"error": str(exc)})
            return

        self._send(201, order)

    def do_GET(self) -> None:  # noqa: N802
        # "/orders/3" -> ["orders", "3"]
        parts = self.path.strip("/").split("/")
        if len(parts) != 2 or parts[0] != "orders":
            self._send(404, {"error": "没有这个接口"})
            return

        try:
            order = get_order(int(parts[1]))
        except ValueError:
            self._send(400, {"error": "订单号必须是数字"})
            return
        except LookupError as exc:
            self._send(404, {"error": str(exc)})
            return

        self._send(200, order)

    def _send(self, code: int, payload: Dict[str, Any]) -> None:
        """统一的 JSON 返回口子。"""
        # ensure_ascii=False 才能让中文原样输出,而不是 咖啡
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """默认每个请求都会往终端打一行日志,跑测试时太吵,这里静音。"""


def make_server(port: int = 8000) -> HTTPServer:
    """造一个服务器对象但先不启动。port=0 表示让操作系统随便挑个空闲端口。"""
    return HTTPServer(("127.0.0.1", port), ShopHandler)


if __name__ == "__main__":
    server = make_server(8000)
    print("已启动:http://127.0.0.1:8000  (Ctrl+C 退出)")
    server.serve_forever()
