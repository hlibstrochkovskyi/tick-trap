# Reading selected MATLAB experiment inputs

`tick_trap.mat5.read_mat5` is a bounded standard-library decoder for the selected
Level-5 MAT records used by the original sampled-data experiments. It reads
finite real double arrays, method labels and requested numeric fields of scalar
structs. It does not restore MATLAB objects, function handles, cells, sparse,
complex or logical arrays, and does not support HDF5/v7.3 files. It executes no
MATLAB code. Unrequested roots are inventoried; unsupported or missing requested
fields raise an error.

The implementation follows the tag, small-element, column-major and compression
structure described by the [MathWorks MAT-File Format
reference](https://www.mathworks.com/help/pdf_doc/matlab/matfile_format.pdf).
It supports the unpadded compressed-variable layout observed in the pinned
experiment files and both byte orders. It is deliberately not a complete MAT
implementation or a validator of every skipped MATLAB object.

```python
from pathlib import Path
from tick_trap.mat5 import read_mat5

record = read_mat5(Path("results.mat").read_bytes(), {
    "t": "numeric", "x": "numeric", "u": "numeric",
    "opts.dt": "numeric", "method": "text",
})
x = record["values"]["x"]
first_position = (x.at(0, 0), x.at(0, 1))
```

Numeric values become exact `Fraction` values of the stored binary floating
point or compact integer representation. For example, a stored double `0.1`
is `3602879701896397/36028797018963968`, not `1/10`. Compact integer storage
inside a double-class array is accepted only when it represents an exact double.
Dimensions and storage lengths must agree. `MatArray.at` uses MATLAB's
column-major order and rejects invalid indices.

Input size and expanded compressed output are separately limited to 64 MiB by
default; selected values are limited to two million. Excessive nesting,
duplicates, truncated elements, invalid compression, nonfinite selected data and
unknown requested types are errors. These are input-integrity checks, not a
formal program proof or a general parser-security claim.

Successfully reading a file does not establish state/control alignment, an
execution horizon, actuator admissibility, source-controller fidelity or
continuous safety. Those require a separate model-specific audit. In particular,
saved samples and numerical barrier values must not be promoted to validated
continuous-trajectory certificates. A missing certificate remains unknown.
