"""订单模块:算总价 + 存进 sqlite 数据库。

它和 price 模块是「合作关系」:自己算数量乘单价,
但「怎么显示给人看」这件事交给 price.format_price。
这种跨模块 + 落盘的行为,就是集成测试要盯的东西。
"""

import sqlite3
from contextlib import closing
from typing import Any, Dict, Optional

from myshop.price import format_price

# 默认数据库文件。测试时会传一个临时路径进来,免得污染真实数据。
DB_PATH = "myshop.db"

# 订单长什么样:就是一个普通字典,键是字符串,值随意。
Order = Dict[str, Any]


def _path(db_path: Optional[str]) -> str:
    """没指定数据库就用默认的那个。"""
    return db_path if db_path else DB_PATH


def init_db(db_path: Optional[str] = None) -> None:
    """建表。IF NOT EXISTS 保证重复调用也不报错。"""
    # closing(...) 保证用完一定关掉连接,哪怕中间抛异常
    with closing(sqlite3.connect(_path(db_path))) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS orders ("
            "  id          INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  item        TEXT    NOT NULL,"
            "  qty         INTEGER NOT NULL,"
            "  total_cents INTEGER NOT NULL"
            ")"
        )
        conn.commit()


def create_order(
    item: str,
    unit_cents: int,
    qty: int,
    db_path: Optional[str] = None,
) -> Order:
    """下一单:校验 -> 算钱 -> 写库 -> 返回订单。

    注意顺序:所有可能抛异常的事情都必须发生在 INSERT **之前**。
    否则订单已经写进数据库了才报错,库里就留下了脏数据。
    """
    # ---- 1. 先把所有校验做完 ----
    if qty <= 0:
        raise ValueError("数量必须大于 0")
    if unit_cents < 0:
        raise ValueError("单价不能为负数")

    total_cents = unit_cents * qty

    # ---- 2. 再把所有可能抛异常的计算做完 ----
    # format_price 对负数会 raise。放在写库前面调用,
    # 保证「要么整单成功,要么库里什么都没有」。
    total_text = format_price(total_cents)

    # ---- 3. 最后才动数据库 ----
    path = _path(db_path)
    init_db(path)

    with closing(sqlite3.connect(path)) as conn:
        cur = conn.execute(
            "INSERT INTO orders (item, qty, total_cents) VALUES (?, ?, ?)",
            (item, qty, total_cents),
        )
        # lastrowid 在类型上可能是 None,用 or 0 兜底,mypy 才不会报错
        order_id = cur.lastrowid or 0
        conn.commit()

    return {
        "id": order_id,
        "item": item,
        "qty": qty,
        "total_cents": total_cents,
        # ↓↓↓ 这一行就是「跨模块协作」:订单模块用了价格模块的结果
        "total_text": total_text,
    }


def get_order(order_id: int, db_path: Optional[str] = None) -> Order:
    """按 id 把订单从数据库读回来。读不到就抛 LookupError。"""
    path = _path(db_path)
    init_db(path)

    with closing(sqlite3.connect(path)) as conn:
        row = conn.execute(
            "SELECT id, item, qty, total_cents FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()

    if row is None:
        raise LookupError(f"订单 {order_id} 不存在")

    return {
        "id": row[0],
        "item": row[1],
        "qty": row[2],
        "total_cents": row[3],
        "total_text": format_price(row[3]),
    }
