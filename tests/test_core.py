import unittest

from http_cache_directive_parser import parse_cache_control, CacheControlError


class ParseCacheControlTests(unittest.TestCase):
    def test_empty_string_returns_empty_dict(self):
        self.assertEqual(parse_cache_control(""), {})

    def test_whitespace_only_returns_empty_dict(self):
        self.assertEqual(parse_cache_control("   \t  "), {})

    def test_single_flag_directive(self):
        self.assertEqual(parse_cache_control("no-store"), {"no-store": True})

    def test_multiple_flag_directives(self):
        self.assertEqual(
            parse_cache_control("no-store, no-cache, must-revalidate"),
            {"no-store": True, "no-cache": True, "must-revalidate": True},
        )

    def test_numeric_value_becomes_int(self):
        self.assertEqual(parse_cache_control("max-age=60"), {"max-age": 60})
        self.assertIsInstance(parse_cache_control("max-age=60")["max-age"], int)

    def test_quoted_string_value_is_unquoted(self):
        self.assertEqual(
            parse_cache_control('no-cache="Set-Cookie"'),
            {"no-cache": "Set-Cookie"},
        )

    def test_quoted_string_with_escaped_quote(self):
        self.assertEqual(
            parse_cache_control(r'private="a\"b"'),
            {"private": 'a"b'},
        )

    def test_quoted_string_with_comma_inside(self):
        # A comma inside a quoted string must not be treated as a separator.
        self.assertEqual(
            parse_cache_control('no-cache="a, b"'),
            {"no-cache": "a, b"},
        )

    def test_whitespace_around_equals_is_trimmed(self):
        self.assertEqual(
            parse_cache_control("max-age =  30"),
            {"max-age": 30},
        )

    def test_whitespace_around_commas_is_trimmed(self):
        self.assertEqual(
            parse_cache_control("no-store ,  no-cache"),
            {"no-store": True, "no-cache": True},
        )

    def test_duplicate_directive_last_wins(self):
        # Documented behaviour: last occurrence wins.
        self.assertEqual(
            parse_cache_control("max-age=10, max-age=20"),
            {"max-age": 20},
        )

    def test_non_numeric_token_value_stays_string(self):
        self.assertEqual(
            parse_cache_control("stale-while-revalidate=abc"),
            {"stale-while-revalidate": "abc"},
        )

    def test_directive_names_are_lowercased(self):
        # RFC 7230 says field directives are case-insensitive; we normalize.
        self.assertEqual(
            parse_cache_control("NO-STORE, Max-Age=5"),
            {"no-store": True, "max-age": 5},
        )

    def test_trailing_comma_is_accepted(self):
        # Lenient parsing: a trailing comma after the last directive is
        # tolerated, matching the behaviour of most deployed caches.
        self.assertEqual(
            parse_cache_control("no-store,"),
            {"no-store": True},
        )

    def test_unterminated_quoted_string_raises(self):
        with self.assertRaises(CacheControlError):
            parse_cache_control('no-cache="unfinished')

    def test_equals_with_no_value_raises(self):
        with self.assertRaises(CacheControlError):
            parse_cache_control("max-age=")

    def test_dangling_backslash_in_quoted_string_raises(self):
        with self.assertRaises(CacheControlError):
            parse_cache_control(r'no-cache="a\\')

    def test_missing_comma_between_directives_raises(self):
        with self.assertRaises(CacheControlError):
            parse_cache_control("no-store no-cache")

    def test_none_input_raises(self):
        with self.assertRaises(CacheControlError):
            parse_cache_control(None)  # type: ignore[arg-type]

    def test_mixed_flags_and_values(self):
        self.assertEqual(
            parse_cache_control('public, max-age=300, no-cache="Cookie"'),
            {"public": True, "max-age": 300, "no-cache": "Cookie"},
        )


if __name__ == "__main__":
    unittest.main()
