"""H08 验收（纯函数层）：复核员只读碰壁时，任何 helper 都不得把错误伪装成入队成功。

这些断言必须严格为 None / False——不接受“是 None 或 dict”之类的恒真写法。
"""

from desk.false_enqueue import mask_error_as_success, should_fake
from desk.h08_extra_trap import wrap_forbidden


def test_wrap_forbidden_never_fakes_enqueue_success():
    # 碰壁必须原样透出 403，不允许返回伪造的“已入队成功”载荷
    assert wrap_forbidden("当前账号只读，不能提交刀补") is None


def test_no_error_status_is_masked_as_success():
    for status_code in (400, 401, 403, 422, 500):
        assert should_fake(status_code) is False
        assert mask_error_as_success(status_code, "只读") is None
