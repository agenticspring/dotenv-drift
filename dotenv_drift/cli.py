"""Command-line interface for dotenv-drift.

Exit codes:
  0 - no drift (files are in sync)
  1 - drift detected (missing / extra in --strict mode / empty / duplicates)
  2 - error (missing file, unreadable file, or parse error)
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .diff import DriftReport, diff
from .parser import parse_file

EXIT_OK = 0
EXIT_DRIFT = 1
EXIT_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dotenv-drift",
        description=(
            "Detect drift between a reference environment file "
            "(.env.example) and an actual environment file (.env)."
        ),
    )
    p.add_argument("--version", action="version", version="dotenv-drift " + __version__)
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("check", help="compare reference vs actual env files")
    c.add_argument(
        "--reference",
        default=".env.example",
        help="reference env file (default: .env.example)",
    )
    c.add_argument(
        "--actual",
        default=".env",
        help="actual env file to check (default: .env)",
    )
    c.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    c.add_argument(
        "--strict",
        action="store_true",
        help="treat extra keys as drift (fail) instead of warning",
    )
    c.add_argument(
        "--ignore",
        default="",
        metavar="KEY,KEY2",
        help="comma-separated keys to exclude from the check",
    )
    return p


def _report_json(report: DriftReport, strict: bool, has_drift: bool) -> str:
    payload = {
        "drift": has_drift,
        "strict": strict,
        "missing": report.missing,
        "extra": report.extra,
        "empty": report.empty,
        "duplicates": [
            {"key": key, "source": source}
            for key, source in report.duplicate_keys
        ],
        "parse_errors": [
            {"source": source, "message": message}
            for source, message in report.parse_errors
        ],
    }
    return json.dumps(payload, indent=2)


def _report_text(report: DriftReport, strict: bool, has_drift: bool) -> str:
    lines = []
    if report.missing:
        lines.append("MISSING keys (in reference, not in actual):")
        lines.extend("  - " + k for k in report.missing)
    if report.extra:
        level = "DRIFT" if strict else "warning"
        lines.append("EXTRA keys (in actual, not in reference) [%s]:" % level)
        lines.extend("  - " + k for k in report.extra)
    if report.empty:
        lines.append("EMPTY values:")
        lines.extend("  - " + k for k in report.empty)
    if report.duplicate_keys:
        lines.append("DUPLICATE keys:")
        lines.extend("  - %s (in %s file)" % (k, src) for k, src in report.duplicate_keys)
    if not has_drift:
        lines.append("OK: no drift detected.")
    return "\n".join(lines)


def _fail(msg: str) -> int:
    print("error: " + msg, file=sys.stderr)
    return EXIT_ERROR


def run_check(args: argparse.Namespace) -> int:
    if not os.path.isfile(args.reference):
        return _fail("reference file not found: %s" % args.reference)
    if not os.path.isfile(args.actual):
        return _fail("actual file not found: %s" % args.actual)

    try:
        reference = parse_file(args.reference)
    except OSError as exc:
        return _fail("cannot read reference file: %s" % exc)
    except UnicodeDecodeError as exc:
        return _fail("cannot decode reference file as utf-8: %s" % exc)
    try:
        actual = parse_file(args.actual)
    except OSError as exc:
        return _fail("cannot read actual file: %s" % exc)
    except UnicodeDecodeError as exc:
        return _fail("cannot decode actual file as utf-8: %s" % exc)

    ignore = [k.strip() for k in args.ignore.split(",") if k.strip()]
    report = diff(reference, actual, ignore=ignore)

    if report.parse_errors:
        for source, message in report.parse_errors:
            print("parse error in %s: %s" % (source, message), file=sys.stderr)
        return EXIT_ERROR

    drift_parts = list(report.missing) + list(report.empty) + [
        key for key, _ in report.duplicate_keys
    ]
    if args.strict:
        drift_parts += list(report.extra)
    has_drift = bool(drift_parts)

    if args.format == "json":
        print(_report_json(report, args.strict, has_drift))
    else:
        print(_report_text(report, args.strict, has_drift))
    return EXIT_DRIFT if has_drift else EXIT_OK


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "check":
        return run_check(args)
    return EXIT_ERROR  # unreachable


if __name__ == "__main__":
    sys.exit(main())
