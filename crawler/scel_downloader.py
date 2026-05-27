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
    
    def download_dict(self, dict_id: str, name: str) -> Optional[str]:
        """下载单个词库"""
        try:
            download_url = self.get_dict_download_url(dict_id)
            if not download_url:
                return None
            
            resp = self.session.get(download_url, timeout=30)
            
            # 保存文件
            safe_name = re.sub(r'[^\w\u4e00-\u9fff-]', '_', name)
            filepath = os.path.join(self.output_dir, f"{safe_name}.scel")
            
            with open(filepath, 'wb') as f:
                f.write(resp.content)
            
            return filepath
        except Exception as e:
            print(f"下载词库 {name} 失败: {e}")
            return None
    
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
