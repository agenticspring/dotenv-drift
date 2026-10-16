"""Unit tests for the drift diff engine."""

import unittest

from dotenv_drift.diff import diff
from dotenv_drift.parser import parse_text


def env(text):
    return parse_text(text)


class TestDiff(unittest.TestCase):
    def test_no_drift(self):
        ref = env("A=1\nB=2\n")
        act = env("A=1\nB=2\n")
        report = diff(ref, act)
        self.assertTrue(report.is_clean)
        self.assertEqual(report.missing, [])
        self.assertEqual(report.extra, [])

    def test_missing_keys(self):
        ref = env("A=1\nB=2\nC=3\n")
        act = env("A=1\n")
        report = diff(ref, act)
        self.assertEqual(report.missing, ["B", "C"])
        self.assertFalse(report.is_clean)

    def test_extra_keys(self):
        ref = env("A=1\n")
        act = env("A=1\nEXTRA=1\n")
        report = diff(ref, act)
        self.assertEqual(report.extra, ["EXTRA"])

    def test_empty_values(self):
        ref = env("A=1\nB=2\n")
        act = env("A=1\nB=\n")
        report = diff(ref, act)
        self.assertEqual(report.empty, ["B"])

    def test_duplicates_reported_with_source(self):
        ref = env("A=1\nA=2\n")
        act = env("B=1\nB=2\n")
        report = diff(ref, act)
        self.assertIn(("A", "reference"), report.duplicate_keys)
        self.assertIn(("B", "actual"), report.duplicate_keys)

    def test_ignore_excludes_keys(self):
        ref = env("A=1\nB=2\n")
        act = env("A=1\nC=3\n")
        report = diff(ref, act, ignore=["B", "C"])
        self.assertTrue(report.is_clean)

    def test_different_values_are_not_drift(self):
        ref = env("A=example-value\n")
        act = env("A=real-value\n")
        report = diff(ref, act)
        self.assertTrue(report.is_clean)

    def test_parse_errors_propagate(self):
        ref = env("BAD LINE\nA=1\n")
        act = env("A=1\n")
        report = diff(ref, act)
        self.assertTrue(any(src == "reference" for src, _ in report.parse_errors))

    def test_results_sorted(self):
        ref = env("Z=1\nM=2\nA=3\n")
        act = env("Q=1\n")
        report = diff(ref, act)
        self.assertEqual(report.missing, ["A", "M", "Z"])
        self.assertEqual(report.extra, ["Q"])


if __name__ == "__main__":
    unittest.main()
