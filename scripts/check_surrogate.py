"""检查 surrogate pair 问题"""
word = '𪨊'
pinyin = 'song'

# 测试 UTF-16LE 编码
word_utf16 = word.encode('utf-16-le')
pinyin_utf16 = pinyin.encode('utf-16-le')

print(f'Word: {repr(word)}')
print(f'Word UTF-16LE bytes: {word_utf16.hex()}')
print(f'Word length in UTF-16: {len(word_utf16)} bytes')
print(f'Pinyin UTF-16LE bytes: {pinyin_utf16.hex()}')

# 构建器计算
from src.builder_win10 import Win10MSPinyinBuilder

builder = Win10MSPinyinBuilder()
builder.add_word(word, pinyin, 1)
data = builder.build()

# 检查数据
phrase_start = 0x40 + 4  # header + offset
print(f'\nPhrase data at start: {data[phrase_start:phrase_start+30].hex()}')
print(f'Expected magic: 10001000')
print(f'Actual first 4 bytes: {data[phrase_start:phrase_start+4].hex()}')
