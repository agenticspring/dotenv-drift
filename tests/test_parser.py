"""Unit tests for the .env parser."""

import os
import tempfile
import unittest

from dotenv_drift.parser import ParsedEnv, parse_file, parse_text


class TestParserBasics(unittest.TestCase):
    def test_simple_key_value(self):
        env = parse_text("FOO=bar\n")
        self.assertEqual(env.values, {"FOO": "bar"})
        self.assertEqual(env.duplicates, [])
        self.assertEqual(env.errors, [])

    def test_blank_lines_and_comments_ignored(self):
        env = parse_text("\n# a comment\n   # indented comment\nFOO=bar\n")
        self.assertEqual(env.values, {"FOO": "bar"})

    def test_export_prefix(self):
        env = parse_text("export FOO=bar\nexport  BAZ=qux\n")
        self.assertEqual(env.values, {"FOO": "bar", "BAZ": "qux"})

    def test_value_containing_equals(self):
        env = parse_text("DATABASE_URL=postgresql://user:pass@localhost:5432/app?a=b\n")
        self.assertEqual(
            env.values["DATABASE_URL"],
            "postgresql://user:pass@localhost:5432/app?a=b",
        )

    def test_inline_comment_stripped(self):
        env = parse_text("FOO=bar # this is a comment\n")
        self.assertEqual(env.values["FOO"], "bar")

    def test_hash_inside_quotes_kept(self):
        env = parse_text('FOO="bar # not a comment"\nBAZ=\'qux # kept\'\n')
        self.assertEqual(env.values["FOO"], "bar # not a comment")
        self.assertEqual(env.values["BAZ"], "qux # kept")

    def test_single_quotes_literal(self):
        env = parse_text("FOO='a\\nb'\n")
        self.assertEqual(env.values["FOO"], "a\\nb")

    def test_double_quotes_basic_escapes(self):
        env = parse_text('FOO="a\\nb\\tc\\\\d\\"e"\n')
        self.assertEqual(env.values["FOO"], 'a\nb\tc\\d"e')

    def test_double_quotes_unknown_escape_keeps_backslash(self):
        env = parse_text('FOO="a\\qb"\n')
        self.assertEqual(env.values["FOO"], "a\\qb")

    def test_empty_value(self):
        env = parse_text("FOO=\n")
        self.assertEqual(env.values["FOO"], "")

    def test_duplicates_collected(self):
        env = parse_text("FOO=one\nBAR=x\nFOO=two\nFOO=three\n")
        self.assertEqual(env.duplicates, ["FOO"])
        self.assertEqual(env.values["FOO"], "three")  # last wins

    def test_invalid_key_is_error(self):
        env = parse_text("9BAD=oops\nFOO=bar\n")
        self.assertEqual(env.values, {"FOO": "bar"})
        self.assertTrue(any("9BAD" in e for e in env.errors))

    def test_line_without_equals_is_error(self):
        env = parse_text("FOO=bar\nSOMEFLAG\n")
        self.assertEqual(env.values, {"FOO": "bar"})
        self.assertTrue(any("SOMEFLAG" in e or "no '='" in e for e in env.errors))

    def test_keys_method(self):
        env = parse_text("A=1\nB=2\n")
        self.assertEqual(env.keys, {"A", "B"})

    def test_quoted_value_with_equals_and_spaces(self):
        env = parse_text('FOO="a=b c"\n')
        self.assertEqual(env.values["FOO"], "a=b c")

    def test_export_tab_prefix(self):
        env = parse_text("export\tFOO=bar\n")
        self.assertEqual(env.values["FOO"], "bar")

    def test_bom_stripped_from_file(self):
        # Files saved by Windows editors often start with a UTF-8 BOM;
        # it must not corrupt the first key.
        with tempfile.NamedTemporaryFile(
            "wb", suffix=".env", delete=False
        ) as fh:
            fh.write(b"\xef\xbb\xbfFOO=bar\nBAZ=qux\n")
            path = fh.name
        try:
            env = parse_file(path)
        finally:
            os.unlink(path)
        self.assertEqual(env.values, {"FOO": "bar", "BAZ": "qux"})
        self.assertEqual(env.errors, [])


if __name__ == "__main__":
    unittest.main()
