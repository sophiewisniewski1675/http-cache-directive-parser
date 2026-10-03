# HTTP Cache Directive Parser

Parses an HTTP `Cache-Control` header value into a `dict` of directive → value.

```python
from http_cache_directive_parser import parse_cache_control

cc = parse_cache_control("public, max-age=300, no-cache=\"Set-Cookie\"")
# {'public': True, 'max-age': 300, 'no-cache': 'Set-Cookie'}
```

## Why

Inspecting `Cache-Control` by string-matching is fragile: values can be quoted,
numeric, or bare flags, and commas inside quoted strings are not separators.
This library does one thing — turn that string into a dict — with no
dependencies.

## Edge cases

- **Flag directives** (`no-store`, `public`) map to `True`.
- **Numeric values** (`max-age=60`) map to `int`.
- **Quoted values** are unquoted; escaped chars inside quotes are unescaped.
- **Duplicate directives**: last occurrence wins.
- **Unknown directives** are preserved verbatim rather than rejected.
- **Malformed input** (unterminated quote, missing value after `=`, missing
  comma between directives) raises `CacheControlError`.

## Exports

- `parse_cache_control(header: str) -> dict[str, object]`
- `CacheControlError(ValueError)`

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

