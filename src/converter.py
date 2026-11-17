"""
Rime 词库与微软拼音词库互转工具 (mschxudp 格式)

支持:
- Rime → 微软拼音文本格式 (带拼音)
- 微软拼音 (mschxudp) → Rime 格式
"""

import re
from typing import List, Tuple, Dict, Optional
from .parser import MSPinyinParser
from .importer import BatchImporter, RimeConverter
from .format_spec import is_valid_pinyin


class RimeToMSPConverter:
    """Rime 词库转换为微软拼音文本格式"""

    # 常用多字词拼音映射（覆盖高频词汇）
    COMMON_PINYIN = {
        # 数字
        '〇': 'ling', '一': 'yi', '二': 'er', '三': 'san', '四': 'si',
        '五': 'wu', '六': 'liu', '七': 'qi', '八': 'ba', '九': 'jiu',
        '十': 'shi', '百': 'bai', '千': 'qian', '万': 'wan', '亿': 'yi',
        '零': 'ling',
        # 常用单字
        '的': 'de', '了': 'le', '是': 'shi', '我': 'wo', '不': 'bu',
        '人': 'ren', '在': 'zai', '他': 'ta', '有': 'you', '这': 'zhe',
        '中': 'zhong', '大': 'da', '来': 'lai', '上': 'shang', '国': 'guo',
        '个': 'ge', '到': 'dao', '说': 'shuo', '们': 'men', '为': 'wei',
        '子': 'zi', '和': 'he', '你': 'ni', '地': 'di', '出': 'chu',
        '会': 'hui', '时': 'shi', '要': 'yao', '也': 'ye', '生': 'sheng',
        '以': 'yi', '发': 'fa', '可': 'ke', '下': 'xia', '过': 'guo',
        '对': 'dui', '能': 'neng', '年': 'nian', '得': 'de', '看': 'kan',
        '天': 'tian', '如': 'ru', '为': 'wei', '于': 'yu', '之': 'zhi',
        '其': 'qi', '所': 'suo', '者': 'zhe', '自': 'zi', '已': 'yi',
        # 常用双字词
        '我们': 'women', '他们': 'tamen', '自己': 'ziji', '什么': 'shenme',
        '没有': 'meiyou', '可以': 'keyi', '知道': 'zhidao', '一个': 'yige',
        '这个': 'zhege', '那个': 'nage', '怎么': 'zenme', '因为': 'yinwei',
        '所以': 'suoyi', '但是': 'danshi', '如果': 'ruguo', '虽然': 'suiran',
        '中国': 'zhongguo', '北京': 'beijing', '上海': 'shanghai',
        '深圳': 'shenzhen', '广州': 'guangzhou', '杭州': 'hangzhou',
        '成都': 'chengdu', '武汉': 'wuhan', '南京': 'nanjing',
        '重庆': 'chongqing', '西安': 'xian', '天津': 'tianjin',
        '世界': 'shijie', '国家': 'guojia', '公司': 'gongsi',
        '人民': 'renmin', '政府': 'zhengfu', '社会': 'shehui',
        '经济': 'jingji', '文化': 'wenhua', '教育': 'jiaoyu',
        '科技': 'keji', '发展': 'fazhan', '建设': 'jianshe',
        '服务': 'fuwu', '管理': 'guanli', '系统': 'xitong',
        '数据': 'shuju', '信息': 'xinxi', '网络': 'wangluo',
        '安全': 'anquan', '研究': 'yanjiu', '开发': 'kaifa',
        '设计': 'sheji', '工程': 'gongcheng', '项目': 'xiangmu',
        '产品': 'chanpin', '用户': 'yonghu', '市场': 'shichang',
        '投资': 'touzi', '金融': 'jinrong', '保险': 'baoxian',
        '医疗': 'yiliao', '健康': 'jiankang', '环境': 'huanjing',
        '能源': 'nengyuan', '交通': 'jiaotong', '旅游': 'lvyou',
        '体育': 'tiyu', '娱乐': 'yule', '游戏': 'youxi',
        '新闻': 'xinwen', '媒体': 'meiti', '电影': 'dianying',
        '音乐': 'yinyue', '艺术': 'yishu', '历史': 'lishi',
        '文学': 'wenxue', '科学': 'kexue', '技术': 'jishu',
        '数学': 'shuxue', '物理': 'wuli', '化学': 'huaxue',
        '生物': 'shengwu', '天文': 'tianwen', '地理': 'dili',
        '计算机': 'jisuanji', '人工智能': 'rengongzhineng',
        '机器学习': 'jiqixuexi', '深度学习': 'shenduxuexi',
        '数据分析': 'shujufenxi', '软件工程': 'ruanjiangongcheng',
    }

    def __init__(self):
        self.pinyin_map: Dict[str, str] = dict(self.COMMON_PINYIN)

    def get_pinyin(self, text: str) -> Optional[str]:
        """获取文本的无空格拼音字符串。

        策略:
        1. 先查完整词汇表
        2. 词汇表未命中时，逐字查找拼音并拼接
        3. **任何一个字查不到真实拼音时返回 None**——绝不用 'xx' 之类的
           占位符冒充拼音（占位符能通过 is_valid_pinyin 校验，会污染 DAT）。
           调用方必须把 None 当作「无法转换」处理。
        """
        if text in self.pinyin_map:
            return self.pinyin_map[text]

        # 逐字获取拼音
        parts = []
        for char in text:
            pinyin = self.pinyin_map.get(char)
            if not pinyin:
                # 没有可靠读音 -> 明确失败，不伪造
                return None
            parts.append(pinyin)
        return ''.join(parts)

    def convert_file(self, rime_file: str, output_file: str) -> Dict:
        """转换 Rime 词库为微软拼音文本格式

        Args:
            rime_file: Rime 词库文件路径
            output_file: 输出文件路径（制表符分隔: 词条\t拼音）

        Returns:
            转换统计信息
        """
        entries = RimeConverter.parse_rime_dict(rime_file)

        count = 0
        auto_count = 0
        unresolved: List[str] = []
        with open(output_file, 'w', encoding='utf-8') as f:
            for text, pinyin in entries:
                if not pinyin:
                    pinyin = self.get_pinyin(text)
                    if pinyin is None:
                        # 无法确定真实拼音 -> 记录并跳过，绝不写入占位拼音
                        unresolved.append(text)
                        continue
                    auto_count += 1
                # 移除拼音中的空格（mschxudp 格式要求无空格）
                pinyin = pinyin.replace(' ', '')
                if not is_valid_pinyin(pinyin):
                    unresolved.append(text)
                    continue
                f.write(f"{text}\t{pinyin}\n")
                count += 1

        return {
            'total': count,
            'with_pinyin': count - auto_count,
            'auto_pinyin': auto_count,
            'unresolved': len(unresolved),
            'unresolved_words': unresolved[:20],
        }


class MSPToRimeConverter:
    """微软拼音格式转换为 Rime 词库"""

    def __init__(self, msp_file: str = None):
        self.msp_file = msp_file
        self.parser: Optional[MSPinyinParser] = None
        if msp_file:
            self.load(msp_file)

    def load(self, msp_file: str) -> None:
        """加载微软拼音词库"""
        self.msp_file = msp_file
        self.parser = MSPinyinParser()
        self.parser.load(msp_file)

    def convert_file(self, output_file: str, with_pinyin: bool = True) -> int:
        """转换微软拼音词库为 Rime 格式

        Args:
            output_file: 输出文件路径
            with_pinyin: 是否包含拼音

        Returns:
            转换的词条数量
        """
        if not self.parser:
            raise ValueError("请先加载微软拼音词库")

        count = RimeConverter.generate_rime_dict(
            [(e.text, e.pinyin if with_pinyin else '') for e in self.parser.entries],
            output_file,
            include_pinyin=with_pinyin,
        )
        return count


class BidirectionalConverter:
    """双向转换器 - Rime ↔ 微软拼音"""

    def __init__(self):
        self.r2m = RimeToMSPConverter()
        self.m2r = MSPToRimeConverter()

    def rime_to_msp(self, rime_file: str, output_file: str) -> Dict:
        """Rime → 微软拼音文本格式"""
        return self.r2m.convert_file(rime_file, output_file)

    def msp_to_rime(self, msp_file: str, output_file: str, with_pinyin: bool = True) -> int:
        """微软拼音 → Rime"""
        self.m2r.load(msp_file)
        return self.m2r.convert_file(output_file, with_pinyin)


def main():
    """测试转换器"""
    import sys

    if len(sys.argv) < 4:
        print("用法:")
        print("  python converter.py rime2msp <rime_file> <output_file>")
        print("  python converter.py msp2rime <msp_file> <output_file>")
        sys.exit(1)

    cmd = sys.argv[1]
    input_file = sys.argv[2]
    output_file = sys.argv[3]

    converter = BidirectionalConverter()

    if cmd == 'rime2msp':
        print(f"转换 Rime 词库: {input_file} → {output_file}")
        result = converter.rime_to_msp(input_file, output_file)
        print(f"转换完成: {result}")
    elif cmd == 'msp2rime':
        print(f"转换微软拼音词库: {input_file} → {output_file}")
        count = converter.msp_to_rime(input_file, output_file)
        print(f"转换完成: {count} 词条")
    else:
        print(f"未知命令: {cmd}")


if __name__ == '__main__':
    main()
