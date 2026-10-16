"""Hand-rolled .env file parser. stdlib only, no dependencies.

Supported syntax:
  - Blank lines are ignored.
  - Full-line comments start with ``#`` (optionally preceded by whitespace).
  - Inline comments: a ``#`` preceded by whitespace ends the value, unless
    the value is quoted (quotes shield ``#`` inside them).
  - Optional ``export`` prefix (with or without whitespace after it).
  - Unquoted values: trimmed; everything after the first ``=`` belongs to the
    value (so values may contain ``=``).
  - Single-quoted values: taken literally (no escape processing).
  - Double-quoted values: basic escapes are processed (``\\n``, ``\\t``,
    ``\\r``, ``\\\\``, ``\\"``); unknown escapes keep the backslash.
  - Keys must match ``[A-Za-z_][A-Za-z0-9_]*``.
  - Duplicate keys are collected (every occurrence is reported).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Escapes processed inside double-quoted values.
_DOUBLE_QUOTE_ESCAPES = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "\\": "\\",
    '"': '"',
}


@dataclass
class ParsedEnv:
    """Result of parsing one .env-style file."""

    values: dict
    duplicates: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    @property
    def keys(self):
        return set(self.values)


def _strip_inline_comment(value: str) -> str:
    """Remove an inline comment (`` # comment``) outside of quotes."""
    out = []
    i = 0
    n = len(value)
    quote = None
    while i < n:
        ch = value[i]
        if quote is not None:
            out.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < n:
                out.append(value[i + 1])
                i += 1
            elif ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            out.append(ch)
        elif ch == "#" and (i == 0 or value[i - 1] in (" ", "\t")):
            break  # unquoted # preceded by whitespace -> comment
        else:
            out.append(ch)
        i += 1
    return "".join(out).strip()


def _unquote(raw: str) -> str:
    """Remove surrounding quotes and process basic double-quote escapes."""
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
        inner = raw[1:-1]
        if raw[0] == "'":
            return inner  # single quotes: literal
        out = []
        i = 0
        while i < len(inner):
            ch = inner[i]
            if ch == "\\" and i + 1 < len(inner):
                nxt = inner[i + 1]
                out.append(_DOUBLE_QUOTE_ESCAPES.get(nxt, "\\" + nxt))
                i += 2
            else:
                out.append(ch)
                i += 1
        return "".join(out)
    return raw


def parse_line(line: str, lineno: int, duplicates: list, errors: list):
    """Parse a single line. Returns (key, value) or None."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    # Optional `export` prefix.
    if stripped == "export":
        errors.append("line %d: 'export' without assignment" % lineno)
        return None
    if stripped.startswith("export ") or stripped.startswith("export\t"):
        stripped = stripped[len("export"):].strip()
        if not stripped:
            errors.append("line %d: 'export' without assignment" % lineno)
            return None
    if "=" not in stripped:
        errors.append("line %d: no '=' found" % lineno)
        return None
    key, _, raw_value = stripped.partition("=")
    key = key.strip()
    if not KEY_RE.match(key):
        errors.append("line %d: invalid key %r" % (lineno, key))
        return None
    value = _unquote(_strip_inline_comment(raw_value))
    return key, value


def parse_text(text: str) -> ParsedEnv:
    """Parse the full text of a .env-style file."""
    values = {}
    seen = set()
    duplicates = []
    errors = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        result = parse_line(line, lineno, duplicates, errors)
        if result is None:
            continue
        key, value = result
        if key in seen and key not in duplicates:
            duplicates.append(key)
        seen.add(key)
        values[key] = value
    return ParsedEnv(values=values, duplicates=duplicates, errors=errors)


def parse_file(path: str) -> ParsedEnv:
    """Read and parse a .env-style file from disk.

    Files are read as UTF-8; a leading UTF-8 BOM (common in files saved
    by Windows editors) is stripped so it does not corrupt the first key.
    """
    with open(path, "r", encoding="utf-8-sig") as fh:
        return parse_text(fh.read())
