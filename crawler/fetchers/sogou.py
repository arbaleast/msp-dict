"""
搜狗词库抓取器

解析搜狗细胞词库（.scel格式），获取海量中文词条
搜狗词库是国内最大的第三方词库之一，涵盖各行各业的专业词汇

使用方法：
1. 设置环境变量 SOGOU_COOKIE（从搜狗官网获取）
2. 运行 python -m crawler.fetchers.sogou --download 下载词库
3. 使用 fetch() 获取词条
"""

import os
import re
import sys
import struct
import urllib.request
import urllib.error
import urllib.parse
from typing import List, Set, Optional, Dict
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()


# 程序员相关词库 ID 列表
# 从搜狗分类页面提取的实际 download_id
PROGRAMMER_DICTS = [
    (15117, "计算机词汇大全"),      # 计算机词汇
    (15203, "物理词汇大全"),        # 物理词汇
    (15097, "金融财经词汇"),         # 金融财经
]


class SogouFetcher:
    """搜狗词库解析器"""

    def __init__(self, cache_dir: str = None):
        """
        Args:
            cache_dir: 缓存目录，存放下载的词库文件（.scel格式）
        """
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(__file__), '..', '..', '.cache', 'sogou'
        )
        os.makedirs(self.cache_dir, exist_ok=True)

    def fetch(self, limit: int = 10000) -> List[str]:
        """
        获取搜狗词库词条（从本地缓存的 .scel 文件解析）

        Args:
            limit: 最大返回词条数量

        Returns:
            中文词条列表
        """
        words = self._fetch_from_cache()
        return list(words)[:limit]

    def _fetch_from_cache(self) -> Set[str]:
        """从缓存目录解析所有 .scel 文件"""
        words = set()

        if not os.path.exists(self.cache_dir):
            return words

        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.scel'):
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    parsed = self.parse_scel(filepath)
                    words.update(parsed)
                    print(f"[Sogou] Parsed {len(parsed)} words from {filename}")
                except Exception as e:
                    print(f"[Sogou] Error parsing {filename}: {e}")

        return words

    def parse_scel(self, filepath: str) -> Set[str]:
        """
        解析搜狗细胞词库文件（.scel格式）

        Args:
            filepath: .scel 文件路径

        Returns:
            词条集合
        """
        words = set()

        with open(filepath, 'rb') as f:
            data = f.read()

        # 验证魔数: @\x15\x00\x00 + "DCS"
        if not (data.startswith(b'@\x15\x00\x00') and b'DCS' in data[:10]):
            print(f"[Sogou] Invalid scel file: {filepath}")
            return words

        # 读取词库名称（从 offset 28 开始，UTF-16LE）
        try:
            name_text = data[28:92].decode('utf-16le', errors='ignore')
            null_pos = name_text.find('\x00')
            if null_pos > 0:
                dict_name = name_text[:null_pos].strip()
                if dict_name:
                    print(f"[Sogou] Parsing dict: {dict_name}")
        except Exception as e:
            pass

        # 解析词条数据
        # 文件结构:
        # - offset 0-6: 魔数 @\x15\x00\x00DCS
        # - offset 28+: 词库名称 (UTF-16LE)
        # - offset ~5446: 拼音索引表 (0x02 开头)
        # - offset ~9774+: 词条数据块 (0x09 开头)

        i = 0
        while i < len(data) - 10:
            if data[i] == 0x09:
                # 词条块: marker(1) + unknown(1) + pinyin_index(2) + unknown(2) + word_count(2) + words
                i += 1  # skip marker
                i += 1  # skip unknown byte
                i += 2  # skip pinyin_index
                i += 2  # skip unknown
                word_count = struct.unpack('<H', data[i:i+2])[0]
                i += 2

                for _ in range(word_count):
                    if i + 1 >= len(data):
                        break

                    # 读取词条（UTF-16LE，null 结尾）
                    word_chars = []
                    while i + 1 < len(data):
                        char_val = data[i] + (data[i+1] << 8)
                        i += 2
                        if char_val == 0:
                            break
                        if 0x4e00 <= char_val <= 0x9fff:
                            word_chars.append(chr(char_val))
                        else:
                            # 非中文字符，可能需要跳过
                            break

                    if word_chars:
                        word = ''.join(word_chars)
                        # 只保留 2-20 字的中文词条
                        if 2 <= len(word) <= 20:
                            words.add(word)

                    # 跳过额外的 4 字节数据
                    if i + 4 <= len(data):
                        i += 4

            elif data[i] == 0x02:
                # 拼音索引表，跳过
                i += 1
            elif data[i] == 0x01:
                # 跳过整个块
                i += 1
            elif data[i] == 0:
                # 空字节，跳过
                i += 1
            else:
                # 未知数据，跳过
                i += 1

        return words

    def _load_cookie(self) -> Optional[str]:
        """从环境变量加载 Cookie"""
        cookie = os.getenv('SOGOU_COOKIE')
        if not cookie:
            print("[Sogou] 错误: 未设置 SOGOU_COOKIE 环境变量")
            print("请在 .env 文件中设置 SOGOU_COOKIE")
            return None
        return cookie

    def _extract_download_info(self, dict_id: int, name: str) -> Optional[tuple]:
        """
        从详情页提取下载信息（下载ID和编码后的名称）
        
        Args:
            dict_id: 详情页 ID
            name: 词库名称
            
        Returns:
            (download_id, encoded_name) 或 None
        """
        cookie = self._load_cookie()
        if not cookie:
            return None
            
        url = f"https://pinyin.sogou.com/dict/cell.php?id={dict_id}"
        headers = {
            'Cookie': cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://pinyin.sogou.com/dict/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read()
                
            # 尝试从页面提取下载 ID
            # 匹配模式: download_cell.php?id=数字&name=中文名
            patterns = [
                r'download_cell\.php\?id=(\d+)&name=([^"&\s]+)',
                r'["\']([^"\']*download_cell\.php\?id=(\d+)[^"\']*)["\']',
                r'"id"\s*:\s*(\d+).*?"name"\s*:\s*"([^"]+)"',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content.decode('utf-8', errors='ignore'))
                for match in matches:
                    if len(match) == 2:
                        download_id, enc_name = match
                        return (download_id, enc_name)
                    elif len(match) == 3:
                        # 可能是 ("url", download_id, name)
                        download_id = match[1]
                        enc_name = match[2]
                        return (download_id, enc_name)
            
            print(f"[Sogou] 无法从详情页提取下载链接: {name} ({dict_id})")
            return None
            
        except Exception as e:
            print(f"[Sogou] 获取详情页失败: {name} - {e}")
            return None

    def download_dict(self, dict_id: int, name: str) -> bool:
        """
        下载单个搜狗词库（两步下载：先获取详情页，再下载）

        Args:
            dict_id: 词库 ID（如 96）
            name: 词库名称（用于保存文件名）

        Returns:
            是否下载成功
        """
        cookie = self._load_cookie()
        if not cookie:
            return False

        # 清理文件名
        safe_name = name.replace('/', '_').replace('\\', '_')[:50]
        output_path = os.path.join(self.cache_dir, f"{dict_id}_{safe_name}.scel")

        # 检查是否已存在
        if os.path.exists(output_path):
            print(f"[Sogou] 已存在: {name} ({dict_id})")
            return True

        print(f"[Sogou] 下载中: {name} ({dict_id})...")
        
        # 步骤1: 从详情页提取下载信息
        print(f"[Sogou] 提取下载链接...")
        download_info = self._extract_download_info(dict_id, name)
        if not download_info:
            # 如果提取失败，尝试使用直接下载方式
            download_id, enc_name = str(dict_id), urllib.parse.quote(name)
        else:
            download_id, enc_name = download_info
        
        # 步骤2: 使用正确的下载 URL
        # name 参数需要 URL 编码
        encoded_name = urllib.parse.quote(name, safe='')
        download_url = f"https://pinyin.sogou.com/d/dict/download_cell.php?id={download_id}&name={encoded_name}"
        
        headers = {
            'Cookie': cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f'https://pinyin.sogou.com/dict/cell.php?id={dict_id}',
            'Accept': '*/*',
            'Accept-Encoding': 'identity',  # 防止压缩
        }

        try:
            req = urllib.request.Request(download_url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as response:
                content = response.read()
                content_type = response.headers.get('Content-Type', '')
                
            # scel 文件魔数: 4字节 `@` + 3字节 `DCS` + 9字节未知 = `@\x15\x00\x00DCS`
            # 简化为检查开头是否是 `@` 并且包含 DCS
            if not (content.startswith(b'@') and b'DCS' in content[:10]):
                print(f"[Sogou] 失败: {name} - 下载的不是有效的 scel 文件")
                print(f"[Sogou] 响应大小: {len(content)} bytes, Content-Type: {content_type}")
                return False

            with open(output_path, 'wb') as f:
                f.write(content)

            size_kb = len(content) / 1024
            print(f"[Sogou] 成功: {name} -> {output_path} ({size_kb:.1f} KB)")
            return True

        except urllib.error.URLError as e:
            print(f"[Sogou] 网络错误: {name} - {e}")
            return False

    def download_popular(self) -> Dict[str, bool]:
        """
        下载程序员相关的热门词库

        Returns:
            下载结果字典 {词库名: 是否成功}
        """
        print(f"[Sogou] 开始下载 {len(PROGRAMMER_DICTS)} 个词库...")
        print(f"[Sogou] 缓存目录: {self.cache_dir}")
        print("-" * 50)

        results = {}
        for dict_id, name in PROGRAMMER_DICTS:
            results[name] = self.download_dict(dict_id, name)

        print("-" * 50)
        success_count = sum(1 for v in results.values() if v)
        print(f"[Sogou] 下载完成: {success_count}/{len(results)} 成功")

        return results

    def list_cached(self) -> List[str]:
        """列出本地已缓存的 .scel 文件"""
        if not os.path.exists(self.cache_dir):
            return []
        return [f for f in os.listdir(self.cache_dir) if f.endswith('.scel')]


def main():
    """搜狗词库抓取器主入口"""
    import argparse

    parser = argparse.ArgumentParser(description='搜狗词库下载和解析工具')
    parser.add_argument('--download', action='store_true', help='下载程序员相关词库')
    parser.add_argument('--list', action='store_true', help='列出已缓存的词库')
    args = parser.parse_args()

    fetcher = SogouFetcher()

    if args.download:
        # 下载模式
        fetcher.download_popular()
    elif args.list:
        # 列出已缓存文件
        cached = fetcher.list_cached()
        if cached:
            print(f"已缓存 {len(cached)} 个词库:")
            for f in cached:
                print(f"  - {f}")
        else:
            print("暂无缓存词库，使用 --download 下载")
    else:
        # 默认模式：解析已缓存的词库
        print("Testing Sogou fetcher...")
        print(f"Cache dir: {fetcher.cache_dir}")
        print("-" * 40)

        words = fetcher.fetch(limit=1000)
        print(f"\nTotal words: {len(words)}")

        if words:
            length_dist = {}
            for w in words:
                l = len(w)
                length_dist[l] = length_dist.get(l, 0) + 1

            print("\nLength distribution:")
            for l in sorted(length_dist.keys()):
                print(f"  {l}字: {length_dist[l]}")

            print("\nFirst 30 words:")
            for w in list(words)[:30]:
                print(f"  - {w}")
        else:
            print("\nNo .scel files found in cache directory.")
            print("Use --download to download popular dicts for programmers")


if __name__ == '__main__':
    main()
