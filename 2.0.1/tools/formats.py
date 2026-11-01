"""Observed Pokopia LINKDATA variant. Python 3.10+, standard library only."""
from pathlib import Path
from dataclasses import dataclass
import struct
import zlib
import hashlib

def align(n, boundary=128):
    return (n + boundary - 1) // boundary * boundary

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

@dataclass(frozen=True)
class Entry:
    offset: int
    size: int
    stored: int
    flag: int

class Archive:
    def __init__(self, root, tolerate_legacy_stored=False):
        self.root = Path(root)
        self.index = (self.root/'LI_C0_R.IDX').read_bytes()
        if len(self.index) % 32:
            raise ValueError('IDX length is not a multiple of 32')
        self.entries = [Entry(*v) for v in struct.iter_unpack('<QQQQ', self.index)]
        self.data = (self.root/'LD_C0_R.BIN').read_bytes()
        self.tolerate_legacy_stored = tolerate_legacy_stored

    def physical_size(self, i):
        """Padded extent described by a compressed container's own chunk table."""
        e = self.entries[i]
        if not e.flag or not e.size:
            return e.stored
        chunk, count, total = struct.unpack_from('<III', self.data, e.offset)
        if chunk not in (65536, 131072, 524288) or total != e.size:
            raise ValueError('Unexpected compression header')
        size = align(12+4*count)
        for j in range(count):
            size += align(struct.unpack_from('<I', self.data, e.offset+12+4*j)[0])
        if e.offset+size > len(self.data):
            raise ValueError('Physical container extent outside BIN')
        return size

    def read(self, i):
        e = self.entries[i]
        if e.size == 0:
            return b''
        if e.offset + e.stored > len(self.data):
            raise ValueError(f'Out-of-bounds archive entry {i}')
        raw = memoryview(self.data)[e.offset:] if self.tolerate_legacy_stored and e.flag else memoryview(self.data)[e.offset:e.offset+e.stored]
        if not e.flag:
            if e.size > e.stored:
                raise ValueError('Truncated raw entry')
            return bytes(raw[:e.size])
        if e.flag != 1:
            raise ValueError(f'Unknown compression flag {e.flag}')
        chunk_size, count, total = struct.unpack_from('<III', raw)
        if chunk_size not in (65536,131072,524288) or total != e.size or count != (total+chunk_size-1)//chunk_size:
            raise ValueError('Unexpected compression header')
        pos = align(12+4*count)
        parts = []
        for j in range(count):
            stored = struct.unpack_from('<I', raw, 12+j*4)[0]
            expected = min(chunk_size, total-j*chunk_size)
            if pos+stored > len(raw):
                raise ValueError('Truncated compression chunk')
            if stored == expected:
                part = raw[pos:pos+stored]
            else:
                length = struct.unpack_from('<I', raw, pos)[0]
                if length+4 != stored:
                    raise ValueError('Chunk length mismatch')
                decoder = zlib.decompressobj()
                part = decoder.decompress(raw[pos+4:pos+stored]) + decoder.flush()
                if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                    raise ValueError('Invalid zlib stream boundary')
            if len(part) != expected:
                raise ValueError('Decompressed chunk length mismatch')
            parts.append(part)
            pos = align(pos+stored)
        out = b''.join(parts)
        if len(out) != e.size:
            raise ValueError('Decompressed entry size mismatch')
        return out

def compress(data):
    chunks = []
    for pos in range(0, len(data), 65536):
        raw = data[pos:pos+65536]
        comp = zlib.compress(raw, 9)
        encoded = struct.pack('<I', len(comp))+comp
        chunks.append(encoded if len(encoded) < len(raw) else raw)
    out = bytearray(struct.pack('<III',65536,len(chunks),len(data)))
    for chunk in chunks:
        out.extend(struct.pack('<I',len(chunk)))
    out.extend(bytes(align(len(out))-len(out)))
    for chunk in chunks:
        out.extend(chunk)
        out.extend(bytes(align(len(out))-len(out)))
    return bytes(out)

@dataclass
class Table:
    count: int
    version: int
    stride: int
    fields: tuple
    strings: dict

def parse_table(data, versions=(2,)):
    if len(data)<72:
        return None
    count, version = struct.unpack_from('<II',data)
    if version not in versions or not 0<count<100000:
        return None
    choices = []
    for stride, fields in [(8,(0,)),(12,(0,4)),(32,(0,4,8,12,16,20))]:
        end = 64+count*stride
        if end>len(data):
            continue
        strings = {}
        try:
            for row in range(count):
                for field in fields:
                    pos = 64+row*stride+field
                    rel = struct.unpack_from('<i',data,pos)[0]
                    target = pos+rel
                    if not end<=target<len(data):
                        raise ValueError()
                    stop = data.index(0,target)
                    text = data[target:stop].decode('utf-8')
                    if any(ord(c)<32 and c not in '\n\r\t' for c in text):
                        raise ValueError()
                    strings[(row,field)] = text
            choices.append(Table(count,version,stride,fields,strings))
        except (ValueError,struct.error,UnicodeError):
            continue
    return choices[0] if len(choices)==1 else None

def rebuild_table(data, table, changes):
    if not changes:
        return data
    # Preserve complete original string pool and all opaque metadata. Append strings
    # and change only the signed relative pointers requested by the catalog.
    out = bytearray(data)
    pool = {}
    for key, text in sorted(changes.items()):
        if key not in table.strings:
            raise ValueError(f'Unknown text field {key}')
        row, field = key
        if '\0' in text:
            raise ValueError('NUL inside translation')
        encoded = text.encode('utf-8')+b'\0'
        if encoded not in pool:
            pool[encoded] = len(out)
            out.extend(encoded)
        pos = 64+row*table.stride+field
        struct.pack_into('<i',out,pos,pool[encoded]-pos)
    out.extend(bytes(align(len(out),8)-len(out)))
    parsed = parse_table(out, (table.version,))
    if parsed is None or parsed.stride != table.stride:
        raise ValueError('Rebuilt table failed parsing')
    for key, original in table.strings.items():
        if parsed.strings[key] != changes.get(key,original):
            raise ValueError('Rebuilt text mismatch')
    return bytes(out)
