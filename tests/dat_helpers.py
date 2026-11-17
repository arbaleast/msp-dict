"""测试辅助：按 mschxudp 规范独立解析 DAT，避免用被测解析器验证构建器。"""

import struct


def iter_records(data: bytes):
    """返回所有记录字段（独立实现，仅用于断言）。"""
    count = struct.unpack_from('<I', data, 28)[0]
    phrase_start = struct.unpack_from('<I', data, 20)[0]
    phrase_end = struct.unpack_from('<I', data, 24)[0]
    offsets = [struct.unpack_from('<I', data, 64 + i * 4)[0] for i in range(count)]
    offsets.append(phrase_end - phrase_start)

    records = []
    for i in range(count):
        start = phrase_start + offsets[i]
        size = offsets[i + 1] - offsets[i]
        magic, hanzi_offset, position, flag = struct.unpack_from('<IHBB', data, start)
        record_ts = struct.unpack_from('<I', data, start + 12)[0]
        code = data[start + 16:start + hanzi_offset - 2].decode('utf-16-le')
        word = data[start + hanzi_offset:start + size - 2].decode('utf-16-le')
        records.append({
            'index': i,
            'magic': magic,
            'hanzi_offset': hanzi_offset,
            'position': position,
            'flag': flag,
            'record_ts': record_ts,
            'code': code,
            'word': word,
            'size': size,
        })
    return records
