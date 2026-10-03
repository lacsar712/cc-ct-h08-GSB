"""本地/CI 测试设置：用内存 SQLite 跑接口与落盘测试（worker 的行锁逻辑不在此覆盖）。"""

from .settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
