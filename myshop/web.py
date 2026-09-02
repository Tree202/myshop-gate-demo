"""网页层:给第 4 层(E2E)一个真的能点的页面。

为什么要有这一层:
    第 1~3 层测的是函数、模块、HTTP 接口 —— 都不需要浏览器。
    但 E2E 要「像真人一样点」,就必须有页面可点。
    本项目原本只有 JSON 接口,所以那条 E2E 只能挂着 skip;
    这个文件补上最小可点流程,让第 4 层真的跑起来。

它有多小:
    四个页面,一条主流程 —— 首页 → 商品页 → 购物车 → 下单成功。
    **没有会话、没有数据库购物车、没有 JavaScript**:
    数量靠表单的隐藏字段一路传下去。
    这样做不是偷懒,是为了让 E2E 稳定 ——
    服务端一旦存了会话状态,测试之间就会互相污染,
    那正是第 10 页讲的「E2E 抖动」最常见的来源之一。

命名说明:
    本模块用中文标识符,与测试层一致而与其余源码(英文)不同 ——
    它是专为第 4 层测试而建的配套设施,跟着测试的可读性优先原则走。

它不负责算钱:
    价格还是交给 price.format_price,下单还是交给 order.create_order。
    这一层只做「把 HTTP 翻译成函数调用,再把结果翻译成 HTML」。
"""

from http.server import HTTPServer
from typing import Dict, List
from urllib.parse import parse_qs, unquote

from myshop.api import ShopHandler
from myshop.order import create_order

# 只卖一样东西,单价写死在这里 —— 真项目会放数据库,示例项目不必
商品名 = "咖啡"
单价分 = 1250


def _页面(标题: str, 正文: str) -> bytes:
    """套一层最小的 HTML 骨架。lang="zh" 让浏览器按中文断行。

    注意:这里直接拼字符串、没做 HTML 转义 —— 目前插进来的只有
    写死的常量和 int,所以安全。哪天要插用户输入的文本,
    先过 html.escape(),否则就是 XSS。"""
    return (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        f"<title>{标题}</title></head><body>{正文}</body></html>"
    ).encode("utf-8")


class WebHandler(ShopHandler):
    """在原有 JSON 接口之外,再挂上几个 HTML 页面。

    继承 ShopHandler 而不是改它 —— 原来的 /orders 接口和它的 5 条测试
    一个字都不用动,这一层只是往上加。
    """

    def do_GET(self) -> None:  # noqa: N802  (方法名是标准库规定的)
        路径 = unquote(self.path.split("?")[0])

        if 路径 == "/":
            self._发页面(
                200,
                "myshop",
                f'<h1>myshop</h1><ul><li><a href="/item">{商品名}</a></li></ul>',
            )
            return

        if 路径 == "/item":
            self._发页面(
                200,
                商品名,
                f"<h1>{商品名}</h1>"
                f"<p>单价 ¥{单价分 // 100}.{单价分 % 100:02d}</p>"
                '<form method="post" action="/cart">'
                '<label for="qty">数量</label>'
                '<input id="qty" name="qty" type="number" value="1" min="1">'
                '<button type="submit">加入购物车</button>'
                "</form>",
            )
            return

        # 不是页面路由就交回给 JSON 接口层(GET /orders/<id>)
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        路径 = unquote(self.path.split("?")[0])

        if 路径 == "/cart":
            数量 = self._读数量()
            self._发页面(
                200,
                "购物车",
                f"<h1>购物车</h1><p>{商品名} × {数量}</p>"
                '<form method="post" action="/checkout">'
                f'<input type="hidden" name="qty" value="{数量}">'
                '<button type="submit">去结算</button>'
                "</form>",
            )
            return

        if 路径 == "/checkout":
            数量 = self._读数量()
            try:
                订单 = create_order(item=商品名, unit_cents=单价分, qty=数量)
            except ValueError as exc:
                self._发页面(400, "下单失败", f"<h1>下单失败</h1><p>{exc}</p>")
                return
            self._发页面(
                200,
                "下单成功",
                "<h1>下单成功</h1>"
                f'<p>订单号 {订单["id"]}</p>'
                f'<div data-testid="order-total">{订单["total_text"]}</div>',
            )
            return

        # 不是页面路由就交回给 JSON 接口层(POST /orders)
        super().do_POST()

    def _读数量(self) -> int:
        """从表单里读 qty。读不出来就当 1 —— 页面层不做严格校验,
        真正的校验在 order.create_order 里,那才是唯一的一处。"""
        长度 = int(self.headers.get("Content-Length") or 0)
        if not 长度:
            return 1
        表单: Dict[str, List[str]] = parse_qs(self.rfile.read(长度).decode("utf-8"))
        值 = 表单.get("qty", ["1"])[0]
        try:
            return int(值)
        except ValueError:
            return 1

    def _发页面(self, code: int, 标题: str, 正文: str) -> None:
        raw = _页面(标题, 正文)
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def make_web_server(port: int = 8000) -> HTTPServer:
    """造一个带网页的服务器。port=0 表示让操作系统随便挑个空闲端口。"""
    return HTTPServer(("127.0.0.1", port), WebHandler)


if __name__ == "__main__":
    # 同 api.py:输出被重定向或被工具捕获时,Windows 的 stdout 会退回系统代码页,
    # 下面那句中文会直接 UnicodeEncodeError,服务器起不来。原因写在 api.py 里。
    import sys

    _reconfigure = getattr(sys.stdout, "reconfigure", None)
    if _reconfigure is not None:
        _reconfigure(encoding="utf-8", errors="replace")

    server = make_web_server(8000)
    print("已启动:http://127.0.0.1:8000  (Ctrl+C 退出)")
    server.serve_forever()
