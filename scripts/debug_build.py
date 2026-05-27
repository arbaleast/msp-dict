"""调试构建器"""
import struct

# 检查 DAT 文件
with open('output/msp_full.dat', 'rb') as f:
    data = f.read()

phrase_count = struct.unpack('<I', data[28:32])[0]
phrase_start = struct.unpack('<I', data[20:24])[0]
phrase_end = struct.unpack('<I', data[24:28])[0]
phrase_offset_start = struct.unpack('<I', data[16:20])[0]

with open('output/debug.txt', 'w') as f:
    f.write(f'phrase_count: {phrase_count}\n')
    f.write(f'size: {len(data)}\n')
    f.write(f'phrase_start: {phrase_start}\n')
    f.write(f'phrase_end: {phrase_end}\n')
    f.write(f'phrase_offset_start: {phrase_offset_start}\n')
    f.write(f'expected offset table size: {phrase_count * 4}\n')
    f.write(f'offset table range: {phrase_offset_start} to {phrase_offset_start + phrase_count * 4}\n')
