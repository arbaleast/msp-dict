"""
Rime 词库与微软拼音词库互转工具
"""

import re
from typing import List, Tuple, Dict, Optional
from .parser import MSPinyinParser, DictEntry
from exporter import Exporter
from importer import BatchImporter, RimeConverter


class RimeToMSPConverter:
    """Rime 词库转换为微软拼音格式"""
    
    def __init__(self):
        self.pinyin_map: Dict[str, str] = {}
        self._load_pinyin_map()
        
    def _load_pinyin_map(self):
        """加载常用拼音映射表"""
        # 常用字拼音表 (简化版)
        common_pinyin = {
            '一': 'yi', '二': 'er', '三': 'san', '四': 'si', '五': 'wu',
            '六': 'liu', '七': 'qi', '八': 'ba', '九': 'jiu', '十': 'shi',
            '百': 'bai', '千': 'qian', '万': 'wan', '亿': 'yi',
            '零': 'ling', '一': 'yi', '丁': 'ding', '万': 'wan',
            '黑客': 'hei ke', '默认': 'mo ren', '黑色': 'hei se',
            '鼠标': 'shu biao', '键盘': 'jian pan', '屏幕': 'ping mu',
            '电脑': 'dian nao', '手机': 'shou ji', '网络': 'wang luo',
            '软件': 'ruan jian', '硬件': 'ying jian', '系统': 'xi tong',
            '程序': 'cheng xu', '代码': 'dai ma', '开发': 'kai fa',
            '测试': 'ce shi', '部署': 'bu shu', '运行': 'yun xing',
            '启动': 'qi dong', '停止': 'ting zhi', '暂停': 'zan ting',
            '继续': 'ji xu', '退出': 'tui chu', '关闭': 'guan bi',
            '打开': 'da kai', '新建': 'xin jian', '删除': 'shan chu',
            '复制': 'fu zhi', '粘贴': 'nian tie', '剪切': 'jian qie',
            '撤销': 'che xiao', '重做': 'zhong zuo', '保存': 'bao cun',
            '加载': 'jia zai', '刷新': 'shua xin', '刷新': 'shua xin',
            '搜索': 'sou suo', '查找': 'cha zhao', '替换': 'ti huan',
            '全选': 'quan xuan', '取消': 'qu xiao', '确认': 'que ren',
            '取消': 'qu xiao', '确定': 'que ding', '取消': 'qu xiao',
            '关于': 'guan yu', '帮助': 'bang zhu', '设置': 'she zhi',
            '选项': 'xuan xiang', '配置': 'pei zhi', '偏好': 'pian hao',
            '文件': 'wen jian', '文件夹': 'wen jian jia', '目录': 'mu lu',
            '路径': 'lu jing', '地址': 'di zhi', '位置': 'wei zhi',
            '大小': 'da xiao', '时间': 'shi jian', '日期': 'ri qi',
            '名称': 'ming cheng', '类型': 'lei xing', '格式': 'ge shi',
            '模式': 'mo shi', '状态': 'zhuang tai', '类型': 'lei xing',
            '用户': 'yong hu', '密码': 'mi ma', '账号': 'zhang hao',
            '登录': 'deng lu', '注册': 'zhu ce', '退出': 'tui chu',
            '首页': 'shou ye', '登录': 'deng lu', '注册': 'zhu ce',
            '我的': 'wo de', '收藏': 'shou cang', '历史': 'li shi',
            '记录': 'ji lu', '收藏': 'shou cang', '历史': 'li shi',
            '下载': 'xia zai', '上传': 'shang chuan', '播放': 'bo fang',
            '暂停': 'zan ting', '停止': 'ting zhi', '继续': 'ji xu',
            '上一首': 'shang yi shou', '下一首': 'xia yi shou',
            '上一曲': 'shang yi qu', '下一曲': 'xia yi qu',
            '随机': 'sui ji', '循环': 'xun huan', '单曲': 'dan qu',
            '顺序': 'shun xu', '列表': 'lie biao', '歌单': 'ge dan',
            '音乐': 'yin yue', '歌曲': 'ge qu', '歌手': 'ge shou',
            '专辑': 'zhuan ji', '歌词': 'ge ci', '音质': 'yin zhi',
            '音量': 'yin liang', '静音': 'jing yin', '播放': 'bo fang',
            '视频': 'shi pin', '电影': 'dian ying', '电视': 'dian shi',
            '综艺': 'zong yi', '动漫': 'dong man', '游戏': 'you xi',
            '直播': 'zhi bo', '短视频': 'duan shi pin',
        }
        self.pinyin_map.update(common_pinyin)
        
    def get_pinyin(self, text: str) -> str:
        """
        获取文本的拼音
        
        Args:
            text: 中文文本
            
        Returns:
            拼音字符串，如 "ni hao"
        """
        if text in self.pinyin_map:
            return self.pinyin_map[text]
            
        # 尝试逐字获取拼音
        pinyin = ''
        for char in text:
            if char in self.pinyin_map:
                pinyin += self.pinyin_map[char] + ' '
            else:
                pinyin += char  # 保留原字符
                
        return pinyin.strip()
        
    def convert_file(self, rime_file: str, output_file: str) -> Dict:
        """
        转换 Rime 词库为微软拼音格式
        
        Args:
            rime_file: Rime 词库文件路径
            output_file: 输出文件路径
            
        Returns:
            转换统计
        """
        # 解析 Rime 词库
        entries = RimeConverter.parse_rime_dict(rime_file)
        
        # 转换为微软拼音格式并导出
        count = 0
        with open(output_file, 'w', encoding='utf-8') as f:
            for text, pinyin in entries:
                # 如果没有拼音，尝试自动获取
                if not pinyin:
                    pinyin = self.get_pinyin(text)
                    
                f.write(f"{text}\t{pinyin}\n")
                count += 1
                
        return {
            'total': count,
            'with_pinyin': sum(1 for _, p in entries if p),
            'auto_pinyin': count - sum(1 for _, p in entries if p),
        }


class MSPToRimeConverter:
    """微软拼音格式转换为 Rime 词库"""
    
    def __init__(self, msp_file: str = None):
        self.msp_file = msp_file
        self.parser = None
        
        if msp_file:
            self.parser = MSPinyinParser()
            self.parser.load(msp_file)
            
    def load(self, msp_file: str) -> None:
        """加载微软拼音词库"""
        self.msp_file = msp_file
        self.parser = MSPinyinParser()
        self.parser.load(msp_file)
        
    def convert_file(self, output_file: str, with_pinyin: bool = True) -> int:
        """
        转换微软拼音词库为 Rime 格式
        
        Args:
            output_file: 输出文件路径
            with_pinyin: 是否包含拼音 (微软拼音的拼音编码无法直接使用)
            
        Returns:
            转换的词条数量
        """
        if not self.parser:
            raise ValueError("请先加载微软拼音词库")
            
        count = 0
        
        # 生成 Rime 格式
        count = RimeConverter.generate_rime_dict(
            [(e.text, '') for e in self.parser.entries],
            output_file,
            include_pinyin=with_pinyin
        )
        
        return count


class BidirectionalConverter:
    """双向转换器 - Rime ↔ 微软拼音"""
    
    def __init__(self):
        self.r2m_converter = RimeToMSPConverter()
        self.m2r_converter = MSPToRimeConverter()
        
    def rime_to_msp(self, rime_file: str, output_file: str) -> Dict:
        """Rime → 微软拼音"""
        return self.r2m_converter.convert_file(rime_file, output_file)
        
    def msp_to_rime(self, msp_file: str, output_file: str, with_pinyin: bool = False) -> int:
        """微软拼音 → Rime"""
        self.m2r_converter.load(msp_file)
        return self.m2r_converter.convert_file(output_file, with_pinyin)


def main():
    """测试转换器"""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python converter.py rime2msp <rime_file> <output_file>")
        print("  python converter.py msp2rime <msp_file> <output_file>")
        sys.exit(1)
        
    cmd = sys.argv[1]
    input_file = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else 'output.txt'
    
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
