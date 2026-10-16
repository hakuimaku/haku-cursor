"""Minimal pure-Python XCursor reader/writer.

``generate.py`` prefers the real ``xcursorgen`` binary (found through PATH).  This module is
the fallback when it is missing, and is also what ``verify.py`` uses to inspect the result.

File layout (little endian):
    header   : "Xcur", header_size=16, version=0x10000, ntoc
    toc[ntoc]: type, subtype (nominal size), absolute position
    image    : header_size=36, type=0xfffd0002, nominal size, version=1,
               width, height, xhot, yhot, delay_ms, then width*height ARGB32
               (pre-multiplied alpha) pixels
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

MAGIC = b"Xcur"
FILE_HEADER_SIZE = 16
FILE_VERSION = 0x10000
IMAGE_TYPE = 0xFFFD0002
IMAGE_HEADER_SIZE = 36
IMAGE_VERSION = 1


@dataclass
class Frame:
    size: int           # nominal size
    width: int
    height: int
    xhot: int
    yhot: int
    delay: int          # milliseconds (0 for static cursors)
    argb: bytes         # pre-multiplied ARGB32, little endian (B, G, R, A byte order)


def premultiply_rgba(rgba: bytes) -> bytes:
    """Convert straight-alpha RGBA bytes to pre-multiplied BGRA (== little-endian ARGB32)."""
    out = bytearray(len(rgba))
    for i in range(0, len(rgba), 4):
        r, g, b, a = rgba[i], rgba[i + 1], rgba[i + 2], rgba[i + 3]
        if a != 255:
            r, g, b = (r * a + 127) // 255, (g * a + 127) // 255, (b * a + 127) // 255
        out[i], out[i + 1], out[i + 2], out[i + 3] = b, g, r, a
    return bytes(out)


def unpremultiply_to_rgba(argb: bytes) -> bytes:
    out = bytearray(len(argb))
    for i in range(0, len(argb), 4):
        b, g, r, a = argb[i], argb[i + 1], argb[i + 2], argb[i + 3]
        if 0 < a < 255:
            r, g, b = min(255, r * 255 // a), min(255, g * 255 // a), min(255, b * 255 // a)
        out[i], out[i + 1], out[i + 2], out[i + 3] = r, g, b, a
    return bytes(out)


def write(path: Path, frames: list[Frame]) -> None:
    """Write frames in the given order (frames of equal size form that size's animation)."""
    toc_end = FILE_HEADER_SIZE + 12 * len(frames)
    chunks, toc, pos = [], [], toc_end
    for f in frames:
        if len(f.argb) != f.width * f.height * 4:
            raise ValueError("pixel buffer does not match frame dimensions")
        body = struct.pack("<9I", IMAGE_HEADER_SIZE, IMAGE_TYPE, f.size, IMAGE_VERSION,
                           f.width, f.height, f.xhot, f.yhot, f.delay) + f.argb
        toc.append(struct.pack("<3I", IMAGE_TYPE, f.size, pos))
        chunks.append(body)
        pos += len(body)
    data = struct.pack("<4s3I", MAGIC, FILE_HEADER_SIZE, FILE_VERSION, len(frames)) + b"".join(toc) + b"".join(chunks)
    Path(path).write_bytes(data)


def read(path: Path) -> list[Frame]:
    data = Path(path).read_bytes()
    magic, header, _version, ntoc = struct.unpack_from("<4s3I", data, 0)
    if magic != MAGIC or header != FILE_HEADER_SIZE:
        raise ValueError(f"{path}: not an XCursor file")
    frames = []
    for i in range(ntoc):
        ctype, _sub, pos = struct.unpack_from("<3I", data, FILE_HEADER_SIZE + 12 * i)
        if ctype != IMAGE_TYPE:
            continue
        hdr, typ, size, ver, w, h, xh, yh, delay = struct.unpack_from("<9I", data, pos)
        if hdr != IMAGE_HEADER_SIZE or typ != IMAGE_TYPE:
            raise ValueError(f"{path}: corrupt image chunk #{i}")
        pixels = data[pos + hdr: pos + hdr + w * h * 4]
        if len(pixels) != w * h * 4:
            raise ValueError(f"{path}: truncated image chunk #{i}")
        frames.append(Frame(size, w, h, xh, yh, delay, pixels))
    return frames
