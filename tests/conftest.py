"""pytest 全局配置：禁止在源码树写 __pycache__。

是最顶部执行的副作用，保证后续用例 import 时不产生字节码文件。
CI 端同时设置 PYTHONDONTWRITEBYTECODE=1（见 .github/workflows/*.yml）。
"""

import sys

sys.dont_write_bytecode = True
