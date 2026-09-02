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
    # Windows 上如果输出被重定向或被工具捕获(`> log.txt`、`| tee`、编辑器的运行面板),
    # stdout 会退回系统代码页(英文机器 cp1252、简体中文机器 cp936),
    # 下面那句中文就直接 UnicodeEncodeError,服务器根本起不来。
    # 实测:把 PYTHONIOENCODING 清掉之后,python -c "print('中文')" 的退出码就是 1。
    # 直接在终端敲不会犯,因为 Python 对 Windows 控制台走的是另一条路 —— 所以这个坑
    # 只在「别人用工具跑你的项目」时才现形,自己手敲一辈子也遇不到。
    import sys

    # 用 getattr 而不是直接调:reconfigure 只在 TextIOWrapper 上有,
    # stdout 被换成别的对象时(重定向、测试替身)它可以不存在 —— 写成
    # sys.stdout.reconfigure(...) 类型检查会直接判红,这不是迁就工具,
    # 是那个属性本来就是可选的。
    _reconfigure = getattr(sys.stdout, "reconfigure", None)
    if _reconfigure is not None:
        _reconfigure(encoding="utf-8", errors="replace")

    server = make_server(8000)
    print("已启动:http://127.0.0.1:8000  (Ctrl+C 退出)")
    server.serve_forever()
