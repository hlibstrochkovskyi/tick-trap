from fractions import Fraction as F
import struct
import unittest
import zlib

from tick_trap.mat5 import read_mat5


# Fixtures use explicit format bytes, independent of the reader's helpers.
def tag(kind, data, endian='<', small=False):
    if small:
        return struct.pack(endian+'HH', kind, len(data))+data+b'\0'*(4-len(data))
    return struct.pack(endian+'II', kind, len(data))+data+(b'' if kind == 15 else b'\0'*((-len(data)) % 8))


def matrix(name, values, shape=(2, 2), endian='<', storage=9, attributes=6):
    fmt = {2: 'B', 3: 'h', 9: 'd', 13: 'Q'}[storage]
    return tag(14, tag(6, struct.pack(endian+'II', attributes, 0), endian)
               +tag(5, struct.pack(endian+'ii', *shape), endian)
               +tag(1, name.encode(), endian, small=0 < len(name) <= 4)
               +tag(storage, struct.pack(endian+fmt*len(values), *values), endian,
                    small=0 < struct.calcsize(fmt)*len(values) <= 4), endian)


def mat_file(elements, endian='<'):
    header = b'MATLAB 5.0 MAT-file, synthetic format reference'.ljust(116, b' ')
    return header+b'\0'*8+struct.pack(endian+'H', 0x0100)+(b'IM' if endian == '<' else b'MI')+elements


class Mat5Tests(unittest.TestCase):
    def test_binary_float_values_and_column_major_indices_in_both_byte_orders(self):
        for endian in ('<', '>'):
            with self.subTest(endian=endian):
                result = read_mat5(mat_file(matrix('x', (0.1, 2, 3, 4), endian=endian), endian), {'x': 'numeric'})
                x = result['values']['x']
                self.assertEqual(x.shape, (2, 2))
                self.assertEqual(x.at(0, 0), F(3602879701896397, 36028797018963968))
                self.assertNotEqual(x.at(0, 0), F(1, 10))
                self.assertEqual((x.at(1, 0), x.at(0, 1), x.at(1, 1)), (2, 3, 4))
                for indices in ((-1, 0), (0, 2), (True, 0)):
                    with self.assertRaises(ValueError):
                        x.at(*indices)

    def test_unpadded_compressed_variables_and_compact_integer_double_storage(self):
        first = tag(15, zlib.compress(matrix('dt', (1,), (1, 1), storage=2)))
        second = tag(15, zlib.compress(matrix('r', (-40, -30), (2, 1), storage=3)))
        result = read_mat5(mat_file(first+second), {'dt': 'numeric', 'r': 'numeric'})
        self.assertEqual(result['values']['dt'].at(0), 1)
        self.assertEqual(result['values']['r'].values, (F(-40), F(-30)))
        self.assertEqual(result['values']['r'].storage_type, 3)

    def test_requested_scalar_struct_fields_and_text_without_loading_objects(self):
        fields = b'dt'.ljust(8, b'\0')+b'ignored'.ljust(8, b'\0')
        opaque = tag(14, tag(6, struct.pack('<II', 17, 0))+tag(1, b'', small=False))
        scalar = tag(14, tag(6, struct.pack('<II', 2, 0))+tag(5, struct.pack('<ii', 1, 1))
                     +tag(1, b'opts', small=True)+tag(5, struct.pack('<i', 8), small=True)
                     +tag(1, fields)+matrix('', (0.1,), (1, 1))+opaque)
        label = tag(14, tag(6, struct.pack('<II', 4, 0))+tag(5, struct.pack('<ii', 1, 7))
                    +tag(1, b'method')+tag(16, b'm4optim'))
        result = read_mat5(mat_file(scalar+label), {'opts.dt': 'numeric', 'method': 'text'})
        self.assertEqual(result['values']['opts.dt'].at(0), F(0.1))
        self.assertEqual(result['values']['method'], 'm4optim')
        with self.assertRaises(ValueError):
            read_mat5(mat_file(scalar), {'opts.ignored': 'numeric'})

    def test_skipped_roots_are_inventoried_but_missing_or_unsupported_requests_fail(self):
        data = mat_file(matrix('x', (1, 2, 3, 4))+matrix('other', (5,), (1, 1)))
        result = read_mat5(data, {'x': 'numeric'})
        self.assertEqual(result['skipped_roots'], [{'name': 'other', 'class_id': 6}])
        for requested in ({'missing': 'numeric'}, {'x': 'text'}, {'x': 'unsafe_kind'}, {'x..y': 'numeric'}):
            with self.assertRaises(ValueError):
                read_mat5(data, requested)

    def test_nonfinite_complex_and_nonrepresentable_double_requests_are_rejected(self):
        for values, attributes, storage in (((float('nan'),), 6, 9), ((float('inf'),), 6, 9),
                                             ((1,), 6 | 0x800, 9), ((2**53+1,), 6, 13)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                read_mat5(mat_file(matrix('x', values, (1, 1), attributes=attributes, storage=storage)), {'x': 'numeric'})

    def test_compressed_resource_limits_and_truncated_or_trailing_streams_fail(self):
        compressed = mat_file(tag(15, zlib.compress(matrix('x', (0,)*1024, (1024, 1)))))
        for data, limits in ((compressed, {'max_uncompressed_bytes': 512}),
                             (compressed, {'max_values': 10}), (compressed[:-1], {}),
                             (compressed+b'x', {}), (compressed, {'max_values': True})):
            with self.subTest(limits=limits, size=len(data)), self.assertRaises(ValueError):
                read_mat5(data, {'x': 'numeric'}, **limits)
        trailing = mat_file(tag(15, zlib.compress(matrix('x', (1,), (1, 1)))+b'extra'))
        with self.assertRaises(ValueError):
            read_mat5(trailing, {'x': 'numeric'})

    def test_ambiguous_names_invalid_dimensions_and_non_level_five_files_fail(self):
        duplicate = mat_file(matrix('x', (1,), (1, 1))*2)
        invalid_shape = mat_file(matrix('x', (1,), (2, 1)))
        for data in (duplicate, invalid_shape, b'not a MAT file', b'\x89HDF\r\n\x1a\n'+b'\0'*128):
            with self.assertRaises(ValueError):
                read_mat5(data, {'x': 'numeric'})


if __name__ == '__main__':
    unittest.main()
