# dotenv-drift

Detect drift between a reference environment file (`.env.example`) and an actual environment file (`.env`).

Every team knows the pain: a deploy fails at 2 AM because one developer forgot to add `REDIS_URL` to their `.env`, or CI passes locally but crashes in production because a variable was renamed in `.env.example` but never updated everywhere. **dotenv-drift** catches that before it hurts — a zero-dependency CLI that compares your env files and tells you exactly what's out of sync.

## Features

- **Missing keys** — in `.env.example` but absent from `.env`
- **Extra keys** — in `.env` but absent from `.env.example` (warning by default, failing under `--strict`)
- **Empty values** — keys that are present but have no value
- **Duplicate keys** — keys defined more than once (per file, with the source file reported)
- **Real `.env` parser** — comments, blank lines, `export` prefix, single/double-quoted values with basic escapes, inline comments, and values containing `=`
- **Machine-readable JSON output** for CI pipelines
- **Meaningful exit codes**: `0` = in sync, `1` = drift found, `2` = error (missing file / parse error)

## Installation

Requires Python 3.9+. No third-party dependencies — stdlib only.

```bash
git clone https://github.com/agenticspring/dotenv-drift.git
cd dotenv-drift
```

Run directly from the source tree:

```bash
python3 -m dotenv_drift.cli check
```

Or make it importable and add a wrapper script on your `PATH`:

```bash
export PYTHONPATH="$PWD:$PYTHONPATH"
```

## Usage

```bash
# Compare .env.example (reference) vs .env (actual)
python3 -m dotenv_drift.cli check

# Custom file paths
python3 -m dotenv_drift.cli check --reference config/.env.example --actual config/.env

# JSON output for CI
python3 -m dotenv_drift.cli check --format json

# Fail on extra keys too
python3 -m dotenv_drift.cli check --strict

# Ignore keys that intentionally differ (e.g. local-only overrides)
python3 -m dotenv_drift.cli check --ignore DEBUG_PORT,LOCAL_ONLY_FLAG
```

### Exit codes

| Code | Meaning |
| ---- | ------- |
| `0`  | No drift — files are in sync |
| `1`  | Drift detected (missing / empty / duplicate keys; extra keys only with `--strict`) |
| `2`  | Error — file not found, unreadable, or contains a parse error |

Tip for CI: add a step that runs `dotenv-drift check --strict` so a pull request fails if it adds a variable to `.env.example` without documenting every file, or leaves stale keys behind.

## Example

Given this `.env.example`:

```ini
DATABASE_URL=postgresql://user:pass@localhost:5432/app
export REDIS_URL=redis://localhost:6379/0
API_BASE="https://api.example.com/v1?x=1&y=2"
SECRET_NAME='super "quoted" value'  # inline comment
OPTIONAL_FLAG=
```

And this `.env` (note: `OPTIONAL_FLAG` missing, `LOG_LEVEL` empty, `SECRET_NAME` duplicated, `LEGACY_VAR` extra):

```ini
DATABASE_URL=postgresql://user:pass@localhost:5432/app
export REDIS_URL=redis://localhost:6379/0
API_BASE="https://api.example.com/v1?x=1&y=2"
SECRET_NAME='super "quoted" value'
SECRET_NAME=second-occurrence
LOG_LEVEL=
LEGACY_VAR=should-not-be-here
```

Running `python3 -m dotenv_drift.cli check`:

```
MISSING keys (in reference, not in actual):
  - OPTIONAL_FLAG
EXTRA keys (in actual, not in reference) [warning]:
  - LEGACY_VAR
EMPTY values:
  - LOG_LEVEL
DUPLICATE keys:
  - SECRET_NAME (in actual file)
```

Exit code: `1`.

## Parser notes

- Lines starting with `#` (after optional whitespace) are comments; ` # ...` after a value is an inline comment (not inside quotes).
- `export KEY=value` is accepted, with or without whitespace after `export`.
- `'single quoted'` values are literal; `"double quoted"` values process `\n`, `\t`, `\r`, `\\`, `\"` (unknown escapes keep the backslash).
- Everything after the first `=` belongs to the value, so `DATABASE_URL=...?a=b` works.
- Keys must match `[A-Za-z_][A-Za-z0-9_]*`; malformed lines are parse errors (exit code `2`).

## Limitations

- Values are compared by presence only — a different value for the same key is **not** drift (that's expected between environments).
- Multiline values (line continuations) are not supported.
- Only UTF-8 encoded files are supported.
- Escapes are processed only inside double-quoted values.

## License

MIT — see [LICENSE](LICENSE).
