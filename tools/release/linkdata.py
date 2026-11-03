"""Lossless repacking of Pokopia's observed LINKDATA BIN/IDX format."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import struct
import zlib


BIN = "LD_C0_R.BIN"
IDX = "LI_C0_R.IDX"
RECORD = struct.Struct("<QQQQ")
CHUNK_SIZES = (65536, 131072, 524288)


def align(value: int, boundary: int = 128) -> int:
    return (value + boundary - 1) // boundary * boundary


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class Entry:
    offset: int
    size: int
    stored: int
    flag: int


class Archive:
    def __init__(self, root: Path, *, allow_legacy_sizes: bool = False):
        self.index = (root / IDX).read_bytes()
        self.data = (root / BIN).read_bytes()
        if not self.index or len(self.index) % RECORD.size:
            raise ValueError("IDX must contain complete 32-byte records")
        self.entries = [Entry(*values) for values in RECORD.iter_unpack(self.index)]
        self.allow_legacy_sizes = allow_legacy_sizes

    def layout(self, entry: Entry) -> tuple[int, list[int], int]:
        if entry.flag not in (0, 1):
            raise ValueError(f"Unknown compression flag: {entry.flag}")
        if entry.offset + entry.stored > len(self.data):
            raise ValueError("IDX record extends beyond the BIN")
        if not entry.flag or not entry.size:
            if entry.size > entry.stored:
                raise ValueError("Truncated raw record")
            return 0, [], entry.stored
        if entry.offset + 12 > len(self.data):
            raise ValueError("Truncated compression header")
        chunk_size, count, total = struct.unpack_from("<III", self.data, entry.offset)
        if (chunk_size not in CHUNK_SIZES or total != entry.size
                or count != (total + chunk_size - 1) // chunk_size):
            raise ValueError("Unexpected compression header")
        header_end = align(12 + 4 * count)
        if entry.offset + header_end > len(self.data):
            raise ValueError("Truncated chunk table")
        sizes = list(struct.unpack_from(f"<{count}I", self.data, entry.offset + 12))
        extent = header_end + sum(align(size) for size in sizes)
        if entry.offset + extent > len(self.data):
            raise ValueError("Compressed record extends beyond the BIN")
        if extent > entry.stored and not self.allow_legacy_sizes:
            raise ValueError("IDX understates the compressed record size")
        return chunk_size, sizes, max(entry.stored, extent)

    def read(self, entry: Entry) -> bytes:
        chunk_size, sizes, _extent = self.layout(entry)
        if not entry.size:
            return b""
        if not entry.flag:
            return self.data[entry.offset:entry.offset + entry.size]
        pos = entry.offset + align(12 + 4 * len(sizes))
        parts = []
        for i, stored in enumerate(sizes):
            expected = min(chunk_size, entry.size - i * chunk_size)
            block = self.data[pos:pos + stored]
            if stored == expected:
                payload = block
            else:
                if stored < 4 or struct.unpack_from("<I", block)[0] != stored - 4:
                    raise ValueError("Invalid compressed chunk length")
                decoder = zlib.decompressobj()
                payload = decoder.decompress(block[4:], expected + 1)
                if (len(payload) != expected or not decoder.eof
                        or decoder.unused_data or decoder.unconsumed_tail):
                    raise ValueError("Invalid zlib stream or decompressed chunk size")
            if len(payload) != expected:
                raise ValueError("Unexpected decoded chunk size")
            parts.append(payload)
            pos += align(stored)
        return b"".join(parts)


def compress(payload: bytes) -> bytes:
    chunks = []
    for pos in range(0, len(payload), 65536):
        raw = payload[pos:pos + 65536]
        compressed = zlib.compress(raw, 9)
        encoded = struct.pack("<I", len(compressed)) + compressed
        chunks.append(encoded if len(encoded) < len(raw) else raw)
    result = bytearray(struct.pack("<III", 65536, len(chunks), len(payload)))
    for chunk in chunks:
        result.extend(struct.pack("<I", len(chunk)))
    result.extend(bytes(align(len(result)) - len(result)))
    for chunk in chunks:
        result.extend(chunk)
        result.extend(bytes(align(len(result)) - len(result)))
    return bytes(result)


def repack(source: Path, target: Path) -> dict:
    """Keep existing compressed streams; compress raw records only when smaller."""
    source, target = source.resolve(), target.resolve()
    if source == target or source in target.parents or target in source.parents:
        raise ValueError("Source and output must be separate directories")
    archive = Archive(source, allow_legacy_sizes=True)
    target.mkdir(parents=True, exist_ok=True)
    index = bytearray(archive.index)
    compressed_records = 0
    repaired_records = 0
    with (target / BIN).open("xb") as stream:
        for i, entry in enumerate(archive.entries):
            _chunk_size, _sizes, extent = archive.layout(entry)
            encoded = archive.data[entry.offset:entry.offset + extent]
            flag = entry.flag
            repaired_records += extent > entry.stored
            if not flag and entry.size:
                candidate = compress(archive.read(entry))
                if align(len(candidate), 256) < align(len(encoded), 256):
                    encoded, flag = candidate, 1
                    compressed_records += 1
            stream.write(bytes(align(stream.tell(), 256) - stream.tell()))
            offset = stream.tell()
            stream.write(encoded)
            RECORD.pack_into(index, i * RECORD.size, offset, entry.size, len(encoded), flag)
    with (target / IDX).open("xb") as stream:
        stream.write(index)

    # Compare every decoded byte, including banks outside the translation catalog.
    built = Archive(target)
    for i, (before, after) in enumerate(zip(archive.entries, built.entries)):
        if before.size != after.size or archive.read(before) != built.read(after):
            raise ValueError(f"Repacked record {i} differs from the source")
    if len(built.entries) != len(archive.entries):
        raise ValueError("Repacking changed the record count")
    if len(built.data) > len(archive.data):
        raise ValueError("Repacked BIN is larger than the source")
    return {
        "source_bytes": len(archive.data),
        "output_bytes": len(built.data),
        "saved_bytes": len(archive.data) - len(built.data),
        "records_verified": len(built.entries),
        "newly_compressed_records": compressed_records,
        "repaired_size_records": repaired_records,
        "all_decoded_records_identical": True,
    }
