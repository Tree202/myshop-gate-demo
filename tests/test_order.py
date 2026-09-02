"""第 2 层:集成测试(金字塔中间层)。

这一层测什么:
    多个模块拼在一起还对不对 —— order 调用 price 有没有接错,
    数据有没有真的写进 sqlite、换个连接还能不能读回来。
这一层不测什么:
    不测 format_price 的每个边界(那是第 1 层的活,重复测是浪费)。
    不走 HTTP,直接调 Python 函数。

tmp_path 是 pytest 自带的 fixture:每个测试自动分到一个全新的空目录,
跑完自动清理。所以测试之间不会互相污染数据库。
"""

from pathlib import Path

import pytest

from myshop.order import create_order, get_order


def test_下单会把总价算对并且带上价格文案(tmp_path: Path) -> None:
    数据库 = str(tmp_path / "test.db")

    订单 = create_order("咖啡", unit_cents=1250, qty=2, db_path=数据库)

    assert 订单["total_cents"] == 2500
    # 这一行证明 order 模块真的用了 price 模块,而不是自己乱拼字符串
    assert 订单["total_text"] == "¥25.00"


@pytest.mark.p0  # 第 18 页:P0 = 挂了就是生产事故的那一条链路
def test_订单真的落盘了_换个连接还读得到(tmp_path: Path) -> None:
    数据库 = str(tmp_path / "test.db")

    订单 = create_order("键盘", unit_cents=39900, qty=1, db_path=数据库)
    # get_order 会重新 connect 一次数据库,读到说明数据不是只存在内存里
    读回来 = get_order(订单["id"], db_path=数据库)

    assert 读回来["item"] == "键盘"
    assert 读回来["total_cents"] == 39900
    assert 读回来["total_text"] == "¥399.00"


def test_下两单会拿到两个不同的订单号(tmp_path: Path) -> None:
    数据库 = str(tmp_path / "test.db")

    第一单 = create_order("茶", unit_cents=800, qty=1, db_path=数据库)
    第二单 = create_order("茶", unit_cents=800, qty=1, db_path=数据库)

    # 自增主键有没有正常工作,是数据库层面的行为,只能靠集成测试发现
    assert 第一单["id"] != 第二单["id"]


def test_数量为零应该被拦下来并且不写库(tmp_path: Path) -> None:
    数据库 = str(tmp_path / "test.db")

    with pytest.raises(ValueError):
        create_order("咖啡", unit_cents=1250, qty=0, db_path=数据库)

    # 报错之后数据库里不该留下垃圾数据
    with pytest.raises(LookupError):
        get_order(1, db_path=数据库)


def test_单价为负数也要被拦下来并且不写库(tmp_path: Path) -> None:
    """这条测的是「校验顺序」这个容易写错的地方。

    如果 create_order 先 INSERT 再算 format_price,那么负数单价会
    「先把脏数据写进库,然后才抛异常」—— 库里就留下了一条不该存在的订单。
    校验必须全部发生在写库之前。
    """
    数据库 = str(tmp_path / "test.db")

    with pytest.raises(ValueError):
        create_order("退款商品", unit_cents=-100, qty=1, db_path=数据库)

    # 关键断言:异常抛出之后,库里必须一条记录都没有
    with pytest.raises(LookupError):
        get_order(1, db_path=数据库)
