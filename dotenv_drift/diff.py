"""Drift detection between a reference .env file and an actual .env file.

Drift categories:
  - ``missing``: keys present in reference but absent in actual.
  - ``extra``: keys present in actual but absent in reference.
  - ``empty``: keys present in actual with an empty value.
  - ``duplicates``: keys defined more than once in either file.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .parser import ParsedEnv


@dataclass
class DriftReport:
    missing: list = field(default_factory=list)
    extra: list = field(default_factory=list)
    empty: list = field(default_factory=list)
    duplicate_keys: list = field(default_factory=list)  # [(key, source), ...]
    parse_errors: list = field(default_factory=list)  # [(source, message), ...]

    @property
    def is_clean(self) -> bool:
        return not (
            self.missing or self.extra or self.empty or self.duplicate_keys
        )


def _sorted_unique(items):
    return sorted(set(items))


def diff(reference: ParsedEnv, actual: ParsedEnv, ignore=()) -> DriftReport:
    """Compute drift between reference and actual parsed env files."""
    ignored = set(ignore)
    ref_keys = reference.keys - ignored
    act_keys = actual.keys - ignored

    missing = _sorted_unique(k for k in ref_keys if k not in actual.keys)
    extra = _sorted_unique(k for k in act_keys if k not in reference.keys)
    empty = _sorted_unique(k for k in act_keys if actual.values.get(k) == "")

    duplicates = sorted(
        {(key, source) for source, key in
         [("reference", k) for k in reference.duplicates] +
         [("actual", k) for k in actual.duplicates]
         if key not in ignored}
    )

    parse_errors = (
        [("reference", msg) for msg in reference.errors]
        + [("actual", msg) for msg in actual.errors]
    )

    return DriftReport(
        missing=missing,
        extra=extra,
        empty=empty,
        duplicate_keys=duplicates,
        parse_errors=parse_errors,
    )
