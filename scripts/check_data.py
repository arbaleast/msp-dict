"""检查 46275 位置的数据"""
import struct

with open('output/msp_full.dat', 'rb') as f:
    data = f.read()

phrase_start = struct.unpack('<I', data[20:24])[0]
phrase_offset_start = 64

# 获取 46275 的偏移
off = struct.unpack('<I', data[phrase_offset_start + 46275 * 4:phrase_offset_start + 46275 * 4 + 4])[0]
pos = phrase_start + off

print(f'Offset: {off}, pos: {pos}')
print(f'Bytes at pos: {data[pos:pos+20].hex()}')

# 获取前一个正常词条的偏移
off_prev = struct.unpack('<I', data[phrase_offset_start + 46274 * 4:phrase_offset_start + 46274 * 4 + 4])[0]
pos_prev = phrase_start + off_prev
print(f'Prev offset: {off_prev}, pos: {pos_prev}')
print(f'Bytes at prev: {data[pos_prev:pos_prev+20].hex()}')

# 检查 txt 中对应位置
print('\nChecking txt around line 46275...')
with open('output/msp_full.txt', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if i == 46274:
            print(f'Line 46275: {repr(line)}')
            break
        if i == 46275:
            print(f'Line 46276: {repr(line)}')
            break
