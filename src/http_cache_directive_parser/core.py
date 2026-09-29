"""Parse an HTTP Cache-Control header into a structured dictionary.

RFC 7234 §5.2 defines the Cache-Control header as a comma-separated list of
directives, each optionally followed by "=<token>" or \"=\"<quoted-string>\".
This module returns a dict mapping directive name to value, with three
normalizations applied:

* Flag directives (no "=" in source) become True.
* Quoted-string values are unquoted.
* Unknown directives are preserved verbatim rather than rejected, because real
  traffic contains extensions (e.g. ``stale-while-revalidate``) and dropping
  them would silently mislead callers about what the server sent.

Ambiguity decisions (documented in README):
  * Duplicate directive names: last wins. RFC 7234 does not forbid repeats and
    is silent on precedence; "last wins" matches common proxy behaviour and is
    the simplest rule to reason about.
  * delta-seconds values are returned as int when they are all digits; otherwise
    the raw token is kept. We do not clamp to a maximum age of ~68 years per
    RFC 7234 §1.2.1 because callers may want to detect absurd values.
  * Whitespace around commas and around "=" is permitted and trimmed, matching
    the lenient parsing most deployed caches perform.
"""

from __future__ import annotations


class CacheControlError(ValueError):
    """Raised when the Cache-Control header is structurally malformed.

    We only reject inputs we genuinely cannot tokenize: an unterminated
    quoted string, or a token containing an illegal character such as a
    bare double-quote. Everything else is normalized, not rejected.
    """


# Characters RFC 7230 forbids inside a token (token = 1*tchar).
# We use this to reject malformed tokens early rather than silently splitting
# them in confusing ways.
_TOKEN_EXTRA_ALLOWED = set("!#$%&'*+-.^_`|~")


def _is_token_char(ch: str) -> bool:
    return ch.isalnum() or ch in _TOKEN_EXTRA_ALLOWED


def _parse_token(text: str, pos: int) -> tuple[str, int]:
    start = pos
    while pos < len(text) and _is_token_char(text[pos]):
        pos += 1
    if pos == start:
        raise CacheControlError(
            f"expected a token at position {pos} but found {text[pos]!r}"
        )
    return text[start:pos], pos


def _parse_quoted_string(text: str, pos: int) -> tuple[str, int]:
    # pos points at the opening quote.
    assert text[pos] == '"'
    pos += 1
    out: list[str] = []
    while pos < len(text):
        ch = text[pos]
        if ch == "\\":
            if pos + 1 >= len(text):
                raise CacheControlError("dangling backslash in quoted-string")
            # Per RFC 7230 §3.2.6, a backslash escapes exactly one char.
            out.append(text[pos + 1])
            pos += 2
            continue
        if ch == '"':
            return "".join(out), pos + 1
        out.append(ch)
        pos += 1
    raise CacheControlError("unterminated quoted-string in Cache-Control")


def _skip_ows(text: str, pos: int) -> int:
    # OWS = *( SP / HTAB ). We do not treat other whitespace as OWS because
    # a bare CR or LF inside a header field value is already rejected by the
    # HTTP parser layer; accepting it here would mask that bug.
    while pos < len(text) and text[pos] in (" ", "\t"):
        pos += 1
    return pos


def parse_cache_control(header: str) -> dict[str, object]:
    """Parse a Cache-Control header value into a dict.

    Returns a dict where:
      * flag directives (e.g. ``no-store``) map to ``True``;
      * numeric directives (e.g. ``max-age=60``) map to ``int``;
      * quoted or non-numeric token directives map to ``str``.

    Raises ``CacheControlError`` if the header cannot be tokenized.
    """
    if header is None:
        raise CacheControlError("header must be a string, got None")
    if not isinstance(header, str):
        raise CacheControlError(f"header must be a string, got {type(header).__name__}")

    result: dict[str, object] = {}
    pos = _skip_ows(header, 0)
    n = len(header)

    # An empty header is a valid (if useless) Cache-Control value: it carries
    # no directives. We return an empty dict rather than raising.
    if pos >= n:
        return result

    while pos < n:
        name, pos = _parse_token(header, pos)
        name = name.lower()
        pos = _skip_ows(header, pos)

        if pos < n and header[pos] == "=":
            pos += 1
            pos = _skip_ows(header, pos)
            if pos >= n:
                raise CacheControlError("directive has '=' but no value")
            if header[pos] == '"':
                value, pos = _parse_quoted_string(header, pos)
            else:
                raw, pos = _parse_token(header, pos)
                # delta-seconds per RFC 7234 §1.2.1 is 1*DIGIT. We store it as
                # int so callers can do arithmetic without re-parsing. A token
                # like "0x10" stays a string because it is not all digits.
                value: object = int(raw) if raw.isdigit() else raw
            result[name] = value
        else:
            result[name] = True

        pos = _skip_ows(header, pos)
        if pos < n:
            if header[pos] != ",":
                raise CacheControlError(
                    f"expected ',' or end of header at position {pos}, "
                    f"found {header[pos]!r}"
                )
            pos += 1
            pos = _skip_ows(header, pos)

    return result
