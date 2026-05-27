"""调试解析器"""
import struct

with open('output/msp_full.dat', 'rb') as f:
    data = f.read()

phrase_count = struct.unpack('<I', data[28:32])[0]
phrase_start = struct.unpack('<I', data[20:24])[0]
phrase_end = struct.unpack('<I', data[24:28])[0]
phrase_offset_start = 64

# 读取 offset 表
offsets = []
for i in range(phrase_count):
    off = struct.unpack('<I', data[phrase_offset_start + i * 4:phrase_offset_start + i * 4 + 4])[0]
    offsets.append(off)
offsets.append(phrase_end - phrase_start)

# 尝试解析词条
success = 0
errors = 0
for i in range(min(phrase_count, 200000)):  # 检查前 20 万条
    pos = phrase_start + offsets[i]
    next_pos = phrase_start + offsets[i + 1]
    
    try:
        magic = struct.unpack('<I', data[pos:pos + 4])[0]
        if magic != 0x00100010:
            errors += 1
            if errors <= 5:
                print(f'Error at {i}: magic={hex(magic)}, pos={pos}')
            if errors >= 100:
                print(f'Too many errors, stopping at {i}')
                break
        else:
            success += 1
    except Exception as e:
        errors += 1
        if errors <= 5:
            print(f'Exception at {i}: {e}')
        break

print(f'Success: {success}, Errors: {errors}')
print(f'Last few offsets: {offsets[-5:]}')
