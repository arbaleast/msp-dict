"""
Wikidata 抓取器

抓取 Wikidata（https://www.wikidata.org）中文标签的实体名称。
Wikidata 是维基媒体的知识图谱项目，包含全球知识的结构化数据。

抓取策略：
  1. 使用 wbsearchentities API 搜索中文标签的实体（主要方式）
  2. 获取指定实体的中文标签（EntityData API 补充）
"""

import json
import time
import subprocess
from typing import List


class WikidataFetcher:
    """Wikidata 中文实体名称抓取器"""

    # Wikidata MediaWiki API（与维基百科同架构，带 Wikibase 扩展）
    API_URL = "https://www.wikidata.org/w/api.php"

    # Wikidata 实体数据 API
    ENTITY_URL = "https://www.wikidata.org/wiki/Special:EntityData"

    # 用于搜索中文标签的通用主题（覆盖各知识领域）
    SEARCH_TOPICS = [
        # 地理
        "中国", "北京", "上海", "城市", "国家", "河流", "山脉",
        # 人物
        "科学家", "作家", "艺术家", "音乐家", "演员", "运动员",
        # 文化
        "文化", "历史", "节日", "语言", "文学", "哲学",
        # 科技
        "技术", "计算机", "互联网", "软件", "人工智能",
        # 自然科学
        "物理", "化学", "生物", "数学", "医学", "天文",
        # 社会
        "教育", "经济", "法律", "政治", "宗教",
        # 艺术与娱乐
        "电影", "音乐", "绘画", "舞蹈", "建筑",
        # 动植物
        "动物", "植物", "物种", "鸟类", "鱼类",
    ]

    def __init__(self, proxy: str = "http://localhost:7893"):
        """
        Args:
            proxy: 代理地址（Wikidata 可能需要代理才能访问）
        """
        self.proxy = proxy
        if proxy:
            self.curl_cmd = ['curl', '-s', '--proxy', proxy,
                             '-H', 'User-Agent: Mozilla/5.0']
        else:
            self.curl_cmd = ['curl', '-s',
                             '-H', 'User-Agent: Mozilla/5.0']
        # 请求间隔（秒），避免触发限流
        self.request_delay = 0.8

    def fetch(self, limit: int = 50) -> List[str]:
        """
        抓取 Wikidata 中文实体名称

        主要方式：通过中文主题搜索 wbsearchentities API 获取实体中文标签。
        补充方式：若不足则通过随机实体获取更多中文标签。

        Args:
            limit: 抓取数量

        Returns:
            中文实体名称列表
        """
        all_labels = []

        # 方法1：通过主题搜索中文标签实体
        per_topic = max(1, limit // len(self.SEARCH_TOPICS))
        for topic in self.SEARCH_TOPICS:
            labels = self._search_entities(topic, limit=per_topic)
            if labels:
                print(f"[Wikidata] Got {len(labels)} labels from topic '{topic}'")
            all_labels.extend(labels)
            time.sleep(self.request_delay)

            if len(all_labels) >= limit:
                break

        # 方法2：如果搜索到的数量不足，补充获取常见实体的中文标签
        if len(all_labels) < limit:
            remaining = limit - len(all_labels)
            print(f"[Wikidata] Fetching {remaining} common entities as supplement...")
            supplement_labels = self._fetch_common_entities(remaining)
            all_labels.extend(supplement_labels)

        # 去重、过滤并截取
        seen = set()
        result = []
        for label in all_labels:
            label = label.strip()
            if label not in seen and self._is_valid_label(label):
                seen.add(label)
                result.append(label)
                if len(result) >= limit:
                    break

        print(f"[Wikidata] Total valid labels: {len(result)}")
        return result

    def _search_entities(self, search_term: str, limit: int = 10) -> List[str]:
        """
        通过 wbsearchentities API 搜索中文标签的实体

        使用 Wikidata 的 Wikibase 搜索接口：
        action=wbsearchentities&search=xxx&language=zh&limit=xx

        Args:
            search_term: 搜索词
            limit: 数量

        Returns:
            实体中文标签列表
        """
        from urllib.parse import quote
        encoded_search = quote(search_term, safe='')
        url = (
            f"{self.API_URL}"
            f"?action=wbsearchentities"
            f"&search={encoded_search}"
            f"&language=zh"
            f"&limit={limit}"
            f"&format=json"
        )

        try:
            result = subprocess.run(
                self.curl_cmd + [url],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=15
            )

            if result.returncode != 0:
                print(f"[Wikidata] curl failed for '{search_term}': {result.stderr}")
                return []

            return self._parse_search_response(result.stdout)

        except subprocess.TimeoutExpired:
            print(f"[Wikidata] Timeout searching '{search_term}'")
            return []
        except Exception as e:
            print(f"[Wikidata] Error searching '{search_term}': {e}")
            return []

    def _fetch_common_entities(self, limit: int = 10) -> List[str]:
        """
        获取常见 Wikidata 实体的中文标签（兜底方案）

        使用固定的知名实体 Q ID，获取其中文标签。
        这些实体在各知识领域都具有代表性。

        Args:
            limit: 数量

        Returns:
            中文标签列表
        """
        # 知名实体的 Q ID 列表（涵盖各领域）
        known_entities = [
            "Q30",    # 美国
            "Q148",   # 中华人民共和国
            "Q8686",  # 中国
            "Q42",    # 道格拉斯·亚当斯（英文经典示例）
            "Q76",    # 习近平
            "Q9174",  # 韩国
            "Q17",    # 日本
            "Q865",   # 台湾
            "Q96",    # 墨西哥
            "Q55",    # 马来西亚
            "Q189",   # 冰岛
            "Q25224", # 中文
            "Q918",   # 欧洲联盟
            "Q37104", # 习近平（不同 Q ID）
            "Q45713", # 上海
            "Q956",   # 北京
            "Q179654", # 广州
            "Q16552", # 深圳
            "Q5861",  # 成都
            "Q4970",  # 香港
            "Q9161",  # 联想
            "Q153",   # 华为
            "Q135815", # 腾讯
            "Q318",   # 阿里巴巴
            "Q860498", # 百度
        ]

        # 只取需要的数量
        selected = known_entities[:limit * 2]
        labels = []
        for qid in selected:
            label = self._get_entity_label(qid)
            if label:
                labels.append(label)
            time.sleep(self.request_delay)
            if len(labels) >= limit:
                break

        return labels

    def _get_entity_label(self, qid: str) -> str:
        """
        通过 EntityData API 获取实体的中文标签

        https://www.wikidata.org/wiki/Special:EntityData/Qxxx.json
        返回的 JSON 中包含实体各语言的标签(labels)、描述(descriptions)等信息。

        Args:
            qid: 实体的 Q ID，如 "Q30"

        Returns:
            中文标签，若不存在则返回空字符串
        """
        url = f"{self.ENTITY_URL}/{qid}.json"

        try:
            result = subprocess.run(
                self.curl_cmd + [url],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=10
            )

            if result.returncode != 0:
                return ""

            return self._parse_entity_label(result.stdout)

        except Exception as e:
            print(f"[Wikidata] Error fetching entity {qid}: {e}")
            return ""

    def _parse_search_response(self, json_str: str) -> List[str]:
        """
        解析 wbsearchentities API 响应

        返回结构：{"search": [{"id": "Q123", "label": "...", "description": "..."}, ...]}

        Args:
            json_str: JSON 字符串

        Returns:
            中文标签列表
        """
        try:
            data = json.loads(json_str)
            search_results = data.get('search', [])

            labels = []
            for entity in search_results:
                label = entity.get('label', '')
                if label:
                    labels.append(label)

                # 如果 label 解析为空但 display.label 存在，也尝试提取（兼容不同响应格式）
                if not label:
                    display = entity.get('display', {})
                    display_label = display.get('label', {}).get('value', '')
                    if display_label:
                        labels.append(display_label)

            return labels

        except json.JSONDecodeError as e:
            print(f"[Wikidata] JSON parse error: {e}")
            return []

    def _parse_entity_label(self, json_str: str) -> str:
        """
        解析 EntityData JSON 响应，提取中文标签

        entity 结构：{"entities": {"Qxxx": {"labels": {"zh": {"value": "..."}, ...}}}

        Args:
            json_str: JSON 字符串

        Returns:
            中文标签，不存在则返回空字符串
        """
        try:
            data = json.loads(json_str)
            entities = data.get('entities', {})

            for entity_data in entities.values():
                labels = entity_data.get('labels', {})
                # 优先中文标签
                for lang in ['zh', 'zh-cn', 'zh-hans', 'zh-tw']:
                    if lang in labels:
                        value = labels[lang].get('value', '')
                        if value:
                            return value
                # 若无中文标签，尝试英文标签
                if 'en' in labels:
                    return labels['en'].get('value', '')

            return ""

        except json.JSONDecodeError:
            return ""

    def _is_valid_label(self, label: str) -> bool:
        """
        检查实体标签是否有效

        Args:
            label: 实体标签

        Returns:
            是否有效
        """
        # 长度限制
        if len(label) < 2 or len(label) > 25:
            return False

        # 过滤纯英文/数字
        if label.replace(' ', '').replace('-', '').isascii() and \
           not any('\u4e00' <= c <= '\u9fff' for c in label):
            # 允许包含中文字符的混合标签通过
            has_chinese = any('\u4e00' <= c <= '\u9fff' for c in label)
            if not has_chinese:
                return False

        return True


def main():
    """测试 Wikidata 抓取器"""
    fetcher = WikidataFetcher()

    print("Testing Wikidata fetcher...")
    print("=" * 40)

    labels = fetcher.fetch(limit=50)
    print(f"\nTotal valid labels: {len(labels)}")
    print("\nFirst 30 labels:")
    for label in labels[:30]:
        print(f"  - {label}")


if __name__ == '__main__':
    main()
