import os

# 保证从仓库根目录直接跑 pytest 时也能完成 Django 初始化；
# 若外部环境（如 docker / CI）已设置 DJANGO_SETTINGS_MODULE，则以外部为准。
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()
