"""Rime 转换器的拼音真实性测试。

历史问题：未知汉字会被替换成占位符 'xx'，而 'xx' 能通过 is_valid_pinyin
校验，于是伪造拼音会一路混进正式 DAT。现在未知汉字必须被明确拦截。
"""

import json

import pytest

from src.converter import RimeToMSPConverter
from src.format_spec import is_valid_pinyin


@pytest.fixture()
def converter():
    return RimeToMSPConverter()


# --------------------------------------------------------------------------
# get_pinyin
# --------------------------------------------------------------------------

def test_known_word_returns_real_pinyin(converter):
    assert converter.get_pinyin('中国') == 'zhongguo'


def test_known_single_char_returns_real_pinyin(converter):
    assert converter.get_pinyin('中') == 'zhong'


@pytest.mark.parametrize('text', [
    '䶮',      # 生僻字，CJK 扩展 B
    '𠀋',      # 扩展 A
    '鿿',      # 扩展 G
    '中䶮国',  # 混合：中间一个字查不到
])
def test_unknown_hanzi_returns_none_not_placeholder(converter, text):
    """未知汉字必须返回 None，绝不能返回 'xx' 之类的占位符。"""
    pinyin = converter.get_pinyin(text)

    assert pinyin is None, f'{text!r} 被转换成了 {pinyin!r}'
    assert pinyin != 'xx'
    if pinyin is not None:
        assert 'xx' not in pinyin


def test_unknown_hanzi_never_produces_valid_looking_pinyin(converter):
    """占位符 'xx' 本身是合法拼音格式——这正是它当初能混进去的原因。"""
    assert is_valid_pinyin('xx') is True  # 前提：xx 确实是合法格式
    assert converter.get_pinyin('䶮') is None  # 所以必须显式拦截


# --------------------------------------------------------------------------
# convert_file
# --------------------------------------------------------------------------

def _write_rime(path, rows):
    path.write_text('\n'.join('\t'.join(r) for r in rows) + '\n', encoding='utf-8')
    return path


def test_convert_file_skips_unknown_hanzi_instead_of_writing_xx(tmp_path):
    src = _write_rime(tmp_path / 'in.dict.yaml', [
        ('中国', 'zhong guo'),
        ('生僻字', 'sheng bi zi'),
        ('䶮䶮', ''),
    ])
    out = tmp_path / 'out.txt'

    result = RimeToMSPConverter().convert_file(str(src), str(out))

    content = out.read_text(encoding='utf-8')
    assert 'xx' not in content
    assert '䶮' not in content
    # 有真实拼音的词条照常写出
    assert '中国\tzhongguo' in content

    assert result['unresolved'] == 1
    assert result['unresolved_words'] == ['䶮䶮']


def test_convert_file_keeps_original_pinyin_when_present(tmp_path):
    src = _write_rime(tmp_path / 'in.dict.yaml', [('中国', 'zhong guo')])
    out = tmp_path / 'out.txt'

    result = RimeToMSPConverter().convert_file(str(src), str(out))

    assert out.read_text(encoding='utf-8').strip() == '中国\tzhongguo'
    assert result['unresolved'] == 0
    assert result['total'] == 1


def test_convert_file_never_writes_placeholder_pinyin(tmp_path):
    """把仓库里所有已知字都换成生僻字，输出里不允许出现任何伪造拼音。"""
    src = _write_rime(tmp_path / 'in.dict.yaml', [
        ('䶮', ''),
        ('鿿', ''),
        ('𠀋', ''),
    ])
    out = tmp_path / 'out.txt'

    result = RimeToMSPConverter().convert_file(str(src), str(out))

    assert out.read_text(encoding='utf-8').strip() == ''
    assert result['total'] == 0
    assert result['unresolved'] == 3


def test_convert_file_rejects_invalid_pinyin(tmp_path):
    """原始拼音非法（如含数字）时必须跳过，而不是原样写进输出。"""
    src = _write_rime(tmp_path / 'in.dict.yaml', [('测试', 'ce2shi')])
    out = tmp_path / 'out.txt'

    result = RimeToMSPConverter().convert_file(str(src), str(out))

    assert 'ce2shi' not in out.read_text(encoding='utf-8')
    assert result['unresolved'] == 1
