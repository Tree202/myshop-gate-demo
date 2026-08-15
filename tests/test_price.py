"""第 1 层:单元测试(金字塔最底下、数量最多、跑得最快的一层)。

这一层测什么:
    一个纯函数的输入输出,包括正常值和边界值(0、进位、非法输入)。
这一层不测什么:
    不碰数据库、不碰 HTTP、不启动服务。
    如果一个「单元测试」需要连数据库,那它其实已经是集成测试了。
"""

import pytest

from myshop.price import format_price


def test_普通价格() -> None:
    assert format_price(1234) == "¥12.34"


def test_零元是边界值() -> None:
    # 0 很容易被漏掉,专门写一条
    assert format_price(0) == "¥0.00"


def test_不足一角要在前面补零() -> None:
    # 5 分不能显示成 "¥0.5",必须是 "¥0.05"
    assert format_price(5) == "¥0.05"


def test_整数元不能丢掉小数位() -> None:
    assert format_price(10000) == "¥100.00"


def test_负数要报错() -> None:
    # 「该报错的时候有没有报错」也是行为的一部分,同样要测
    with pytest.raises(ValueError):
        format_price(-1)
