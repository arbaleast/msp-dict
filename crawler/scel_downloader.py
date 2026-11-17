"""
搜狗细胞词库下载器

从搜狗输入法细胞词库页面下载 .scel 文件
"""

import os
import re
import requests
from typing import List, Tuple, Optional


class SogouCellDownloader:
    """搜狗细胞词库下载器"""
    
    # 搜狗细胞词库 API
    BASE_URL = "https://pinyin.sogou.com"
    API_URL = "https://pinyin.sogou.com/dict/cate.php"
    DOWNLOAD_URL = "https://pinyin.sogou.com/dict/download.php"
    
    # 常用分类 ID
    CATEGORIES = {
        'game': 1,       # 游戏
        'movie': 2,      # 影视
        'name': 3,       # 名人
        'food': 4,       # 餐饮
        'sport': 5,      # 运动
        'tech': 6,       # 科技
        'nature': 7,     # 自然
        'life': 8,       # 生活
        'culture': 9,    # 文化
        'economy': 10,   # 经济
        'medical': 11,   # 医药
        'internet': 12,  # 互联网
        'literature': 13,# 文学
        'animal': 14,     # 动物
        'place': 15,     # 地名
        'poem': 16,      # 古诗词
        'idiom': 17,     # 成语
    }
    
    def __init__(self, output_dir: str = "scel_files"):
        self.output_dir = output_dir
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        os.makedirs(output_dir, exist_ok=True)
    
    def get_category_dicts(self, category_id: int, page: int = 1) -> List[dict]:
        """获取分类下的词库列表"""
        try:
            params = {
                'id': category_id,
                'page': page
            }
            resp = self.session.get(self.API_URL, params=params, timeout=10)
            resp.encoding = 'utf-8'
            
            dicts = []
            # 解析词库名称和下载链接
            # 格式: <a href="/dict/detail/id/xxx" class="cell">...</a>
            pattern = r'<a href="(/dict/detail/id/\d+)"[^>]*>([^<]+)</a>'
            matches = re.findall(pattern, resp.text)
            
            for href, name in matches:
                dict_id = re.search(r'id/(\d+)', href)
                if dict_id:
                    dicts.append({
                        'id': dict_id.group(1),
                        'name': name.strip(),
                        'href': self.BASE_URL + href
                    })
            
            return dicts
        except Exception as e:
            print(f"获取分类 {category_id} 失败: {e}")
            return []
    
    def get_dict_download_url(self, dict_id: str) -> Optional[str]:
        """获取词库下载链接"""
        try:
            detail_url = f"{self.BASE_URL}/dict/detail/id/{dict_id}"
            resp = self.session.get(detail_url, timeout=10)
            
            # 查找下载链接
            pattern = r"download\((\d+), '([^']+)'\)"
            match = re.search(pattern, resp.text)
            if match:
                return f"{self.DOWNLOAD_URL}?id={match.group(1)}&name={match.group(2)}"
            
            return None
        except Exception as e:
            print(f"获取词库 {dict_id} 下载链接失败: {e}")
            return None
    
    # 下载校验：SCEL 文件头必须是 @ + DCS 标记
    SCEL_MAGIC = b'@'
    SCEL_MARKER = b'DCS'
    MIN_VALID_SIZE = 64

    def _is_valid_scel(self, data: bytes) -> bool:
        """校验下载内容是否是合法的 SCEL 文件（头部魔数 + 非空）。"""
        if len(data) < self.MIN_VALID_SIZE:
            return False
        if not data.startswith(self.SCEL_MAGIC):
            return False
        return self.SCEL_MARKER in data[:16]

    def download_dict(self, dict_id: str, name: str) -> Optional[str]:
        """下载单个词库。

        下载采用「临时文件 + 校验 + 原子重命名」三步走：
        任何一步失败都不会在缓存目录留下半截文件，旧的完整文件也不会被破坏。
        """
        part_path = None
        try:
            download_url = self.get_dict_download_url(dict_id)
            if not download_url:
                return None

            safe_name = re.sub(r'[^\w\u4e00-\u9fff-]', '_', name)
            filepath = os.path.join(self.output_dir, f"{safe_name}.scel")
            part_path = filepath + '.part'

            resp = self.session.get(download_url, timeout=30)
            status = getattr(resp, 'status_code', 200)
            if status != 200:
                print(f"下载词库 {name} 失败: HTTP {status}")
                return None

            content = resp.content
            if not self._is_valid_scel(content):
                print(f"下载词库 {name} 失败: 内容不是合法 SCEL"
                      f"（{len(content)} 字节）")
                return None

            # 先写临时文件，成功后再原子替换正式文件
            with open(part_path, 'wb') as f:
                f.write(content)
            os.replace(part_path, filepath)
            part_path = None
            return filepath
        except Exception as e:
            print(f"下载词库 {name} 失败: {e}")
            return None
        finally:
            # 失败时清理残留的 .part，避免下次被当成有效缓存
            if part_path and os.path.exists(part_path):
                try:
                    os.remove(part_path)
                except OSError:
                    pass
    
    def download_category(self, category: str, max_dicts: int = 10) -> List[str]:
        """下载分类下的词库"""
        if category not in self.CATEGORIES:
            print(f"未知分类: {category}")
            return []
        
        category_id = self.CATEGORIES[category]
        dicts = self.get_category_dicts(category_id)
        
        downloaded = []
        for i, d in enumerate(dicts[:max_dicts]):
            print(f"下载 [{i+1}/{min(max_dicts, len(dicts))}] {d['name']}...")
            filepath = self.download_dict(d['id'], d['name'])
            if filepath:
                downloaded.append(filepath)
        
        return downloaded


def main():
    """测试下载器"""
    import sys
    
    downloader = SogouCellDownloader("scel_files")
    
    # 下载几个分类的词库
    categories = ['game', 'movie', 'food', 'tech']
    
    for cat in categories:
        print(f"\n=== 下载 {cat} 分类 ===")
        files = downloader.download_category(cat, max_dicts=3)
        print(f"下载了 {len(files)} 个词库")


if __name__ == '__main__':
    main()
