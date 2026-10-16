"""Unit tests for the dotenv-drift CLI exit codes and formats."""

import json
import os
import tempfile
import unittest

from dotenv_drift.cli import build_parser, run_check


def write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ref = os.path.join(self.tmp.name, ".env.example")
        self.act = os.path.join(self.tmp.name, ".env")
        write(self.ref, "A=example\nB=example\n")
        write(self.act, "A=real\nB=real\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _args(self, **kwargs):
        parser = build_parser()
        argv = ["check", "--reference", self.ref, "--actual", self.act]
        for key, value in kwargs.items():
            argv += ["--" + key.replace("_", "-"), value]
        return parser.parse_args(argv)

    def test_exit_zero_when_in_sync(self):
        self.assertEqual(run_check(self._args()), 0)

    def test_exit_one_on_missing_key(self):
        write(self.act, "A=real\n")
        self.assertEqual(run_check(self._args()), 1)

    def test_extra_key_is_warning_by_default(self):
        write(self.act, "A=real\nB=real\nSURPRISE=yes\n")
        self.assertEqual(run_check(self._args()), 0)

    def test_extra_key_fails_in_strict_mode(self):
        write(self.act, "A=real\nB=real\nSURPRISE=yes\n")
        args = self._args()
        args.strict = True
        self.assertEqual(run_check(args), 1)

    def test_exit_two_when_file_missing(self):
        args = self._args()
        args.actual = os.path.join(self.tmp.name, ".env.does-not-exist")
        self.assertEqual(run_check(args), 2)

    def test_exit_two_on_parse_error(self):
        write(self.act, "A=real\nB=real\nTHIS LINE IS BROKEN\n")
        self.assertEqual(run_check(self._args()), 2)

    def test_empty_value_is_drift(self):
        write(self.act, "A=real\nB=\n")
        self.assertEqual(run_check(self._args()), 1)

    def test_ignore_flag(self):
        write(self.act, "A=real\n")  # B missing
        args = self._args(ignore="B")
        self.assertEqual(run_check(args), 0)

    def test_json_format_is_valid_json(self):
        write(self.act, "A=real\n")
        args = self._args(format="json")
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = run_check(args)
        self.assertEqual(code, 1)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["missing"], ["B"])
        self.assertTrue(payload["drift"])

    def test_duplicates_are_drift(self):
        write(self.act, "A=real\nA=again\nB=real\n")
        self.assertEqual(run_check(self._args()), 1)


if __name__ == "__main__":
    unittest.main()
