"""
Crawler 模块的导入封装

解决 crawler 作为子模块导入父模块的问题
"""

import sys
from pathlib import Path

# 将项目根目录添加到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.editor import MSPinyinEditor
from src.importer import BatchImporter, PinyinConverter

__all__ = ['MSPinyinEditor', 'BatchImporter', 'PinyinConverter']
