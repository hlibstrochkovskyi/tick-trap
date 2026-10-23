"""Read selected finite real arrays from MATLAB Level-5 files, using stdlib only.

This deliberately bounded reader never instantiates MATLAB classes or function
handles. It supports real double arrays (including compact integer storage),
text, and requested fields of scalar structs. Other roots are inventoried and
skipped. It is an input decoder, not a numerical or physical safety certificate.
"""

from dataclasses import dataclass
from fractions import Fraction
from math import isfinite, prod
import struct
import zlib


@dataclass(frozen=True)
class MatArray:
    shape: tuple
    values: tuple
    storage_type: int

    def at(self, row, column=0):
        if (len(self.shape) != 2 or isinstance(row, bool) or isinstance(column, bool)
                or not isinstance(row, int) or not isinstance(column, int)
                or not 0 <= row < self.shape[0] or not 0 <= column < self.shape[1]):
            raise ValueError("Expected valid two-dimensional MATLAB array indices")
        return self.values[row+self.shape[0]*column]


def read_mat5(data, requested, *, max_uncompressed_bytes=64*1024*1024, max_values=2_000_000):
    """Return selected exact values plus an inventory of skipped roots.

    requested maps dotted scalar-struct paths to 'numeric' or 'text'. Binary
    floating values become their exact rational values, not intended decimals.
    Compression, tags and numeric sizes are checked; unsupported requested data
    or missing fields raise rather than being silently substituted. No MCOS,
    cell, sparse, complex, logical, HDF5/v7.3 or executable object support.
    """
    if (not isinstance(data, bytes) or len(data) < 128
            or not data.startswith(b"MATLAB 5.0 MAT-file")):
        raise ValueError("Expected a MATLAB Level-5 file")
    if (not isinstance(requested, dict) or not requested
            or any(not isinstance(k, str) or not k or any(not p for p in k.split('.'))
                   or v not in ("numeric", "text") for k, v in requested.items())):
        raise ValueError("Expected named numeric/text requests")
    for value in (max_uncompressed_bytes, max_values):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("Reader limits must be positive integers")
    if len(data) > max_uncompressed_bytes:
        raise ValueError("MAT input exceeds byte allowance")
    endian = {b"IM": "<", b"MI": ">"}.get(data[126:128])
    if endian is None or struct.unpack(endian+'H', data[124:126])[0] != 0x0100:
        raise ValueError("Unsupported MAT version or byte order")
    selected, skipped, seen_roots = {}, [], set()
    expanded, value_count = 0, 0

    def elements(raw):
        position = 0
        while position < len(raw):
            if len(raw)-position < 8:
                raise ValueError("Truncated MAT element tag")
            word, size = struct.unpack_from(endian+'II', raw, position)
            # For big endian small tags, the two uint16 fields occur in the
            # opposite halves of a uint32. Normal type tags have high half 0.
            if word >> 16:
                kind, size = struct.unpack_from(endian+'HH', raw, position)
                if not 1 <= size <= 4:
                    raise ValueError("Invalid small MAT element")
                payload = raw[position+4:position+4+size]
                position += 8
            else:
                kind = word
                end = position+8+size
                if end > len(raw):
                    raise ValueError("Truncated MAT element data")
                payload = raw[position+8:end]
                # MATLAB compressed elements have no eight-byte data padding.
                position = end if kind == 15 else position+8+((size+7)//8)*8
                if position > len(raw):
                    raise ValueError("Truncated MAT padding")
            if not 1 <= kind <= 18:
                raise ValueError("Unsupported MAT element tag")
            yield kind, payload

    def expect(parts, kind):
        try:
            actual, payload = next(parts)
        except StopIteration as exc:
            raise ValueError("Missing MAT matrix component") from exc
        if actual != kind:
            raise ValueError("Unexpected MAT matrix component")
        return payload

    def text(payload):
        return payload.decode('utf-8')

    def matrix(raw, path=None, depth=0):
        nonlocal value_count
        if depth > 8:
            raise ValueError("MAT structure depth exceeded")
        parts = iter(elements(raw))
        flags = expect(parts, 6)
        if len(flags) != 8:
            raise ValueError("Invalid MAT array flags")
        attributes = struct.unpack(endian+'II', flags)[0]
        cls = attributes & 255
        if cls == 17:  # An MCOS opaque root has a different header layout.
            name = text(expect(parts, 1)) if path is None else path
            if any(k == name or k.startswith(name+'.') for k in requested):
                raise ValueError("Requested MATLAB object is unsupported")
            skipped.append({"name": name, "class_id": cls})
            return
        dimensions = expect(parts, 5)
        if len(dimensions) < 8 or len(dimensions) % 4 or len(dimensions) > 32:
            raise ValueError("Invalid MAT dimensions")
        shape = struct.unpack(endian+'i'*(len(dimensions)//4), dimensions)
        if any(n < 0 for n in shape):
            raise ValueError("Negative MAT dimensions")
        name = text(expect(parts, 1))
        name = path if path is not None else name
        if path is None and name:
            if name in seen_roots:
                raise ValueError("Duplicate MAT variable name")
            seen_roots.add(name)
        wanted = name in requested
        descendants = [k for k in requested if k.startswith(name+'.')]
        if not wanted and not descendants:
            if path is None:
                skipped.append({"name": name, "class_id": cls})
            return
        if cls == 2 and descendants and not wanted:
            if prod(shape) != 1:
                raise ValueError("Only scalar MAT structs are supported")
            width_data = expect(parts, 5)
            if len(width_data) != 4:
                raise ValueError("Invalid MAT field-name width")
            width = struct.unpack(endian+'i', width_data)[0]
            names_raw = expect(parts, 1)
            if not 1 <= width <= 1024 or len(names_raw) % width:
                raise ValueError("Invalid MAT field names")
            fields = [text(names_raw[i:i+width].split(b'\0', 1)[0]) for i in range(0, len(names_raw), width)]
            if len(fields) > 1024 or any(not f for f in fields) or len(set(fields)) != len(fields):
                raise ValueError("Invalid or repeated MAT field names")
            for field in fields:
                matrix(expect(parts, 14), name+'.'+field, depth+1)
        elif cls == 6 and wanted and requested[name] == "numeric":
            if attributes & (0x0800 | 0x0200):
                raise ValueError("Requested array is complex or logical")
            formats = {1: 'b', 2: 'B', 3: 'h', 4: 'H', 5: 'i', 6: 'I', 7: 'f', 9: 'd', 12: 'q', 13: 'Q'}
            try:
                kind, numbers = next(parts)
            except StopIteration as exc:
                raise ValueError("Missing numeric MAT data") from exc
            if kind not in formats:
                raise ValueError("Unsupported real MAT storage type")
            count, fmt = prod(shape), formats[kind]
            value_count += count
            if value_count > max_values or len(numbers) != count*struct.calcsize(fmt):
                raise ValueError("MAT numeric dimensions or value allowance exceeded")
            values = struct.unpack(endian+fmt*count, numbers)
            if any(not isfinite(v) or isinstance(v, int) and int(float(v)) != v for v in values):
                raise ValueError("Requested MAT array is nonfinite or not exactly representable as double")
            selected[name] = MatArray(shape, tuple(Fraction(v) for v in values), kind)
        elif cls == 4 and wanted and requested[name] == "text":
            try:
                kind, letters = next(parts)
            except StopIteration as exc:
                raise ValueError("Missing MAT text") from exc
            encodings = {1: 'utf-8', 2: 'utf-8', 16: 'utf-8', 4: 'utf-16-le' if endian == '<' else 'utf-16-be',
                         17: 'utf-16-le' if endian == '<' else 'utf-16-be',
                         18: 'utf-32-le' if endian == '<' else 'utf-32-be'}
            if kind not in encodings:
                raise ValueError("Unsupported MAT text encoding")
            value = letters.decode(encodings[kind])
            if len(value) != prod(shape):
                raise ValueError("MAT text dimensions disagree")
            selected[name] = value
        else:
            raise ValueError("Unsupported requested MAT class or path")
        if next(parts, None) is not None:
            raise ValueError("Unexpected trailing MAT matrix component")

    def stream(raw, depth=0):
        nonlocal expanded
        if depth > 8:
            raise ValueError("MAT compression depth exceeded")
        for kind, payload in elements(raw):
            if kind == 15:
                decoder = zlib.decompressobj()
                try:
                    result = decoder.decompress(payload, max_uncompressed_bytes-expanded+1)
                except zlib.error as exc:
                    raise ValueError("Invalid compressed MAT data") from exc
                expanded += len(result)
                if (expanded > max_uncompressed_bytes or not decoder.eof
                        or decoder.unused_data or decoder.unconsumed_tail):
                    raise ValueError("Truncated, trailing or excessive MAT compression")
                stream(result, depth+1)
            elif kind == 14:
                matrix(payload)
            else:
                raise ValueError("Expected MAT array or compressed variable")

    stream(data[128:])
    if set(selected) != set(requested):
        raise ValueError("Missing requested MAT fields: "+', '.join(sorted(set(requested)-set(selected))))
    return {"values": selected, "description": data[:116].rstrip(b'\0 ').decode('ascii'),
            "byte_order": "little" if endian == '<' else "big", "expanded_bytes": expanded,
            "skipped_roots": skipped}
