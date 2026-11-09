"""Scenario text import/export for the browser setup page.

``parse_scenario_text`` accepts TOML or JSON and returns the plain config dict;
``to_toml`` writes the subset of TOML that scenario configs use so that
``tomllib.loads(to_toml(config)) == config`` for any JSON-compatible config.
"""

import json
import math
import tomllib
from typing import Any, Mapping

from .model import ElectionError

MAX_SCENARIO_TEXT = 2_000_000


def parse_scenario_text(text: str) -> dict[str, Any]:
    """Parse pasted scenario text; JSON if it starts with ``{``, otherwise TOML."""
    if not isinstance(text, str) or not text.strip():
        raise ElectionError("paste a TOML or JSON scenario")
    if len(text) > MAX_SCENARIO_TEXT:
        raise ElectionError("scenario text is too large")
    stripped = text.lstrip()
    try:
        value = json.loads(stripped) if stripped.startswith("{") else tomllib.loads(text)
    except json.JSONDecodeError as exc:
        raise ElectionError(f"JSON error at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ElectionError(f"TOML error: {exc}") from exc
    if not isinstance(value, dict):
        raise ElectionError("scenario must be a table/object")
    return value


def _key(key: str) -> str:
    if key and all(c.isalnum() or c in "_-" for c in key):
        return key
    return json.dumps(key)


def _value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ElectionError("scenario values must be finite")
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_value(item) for item in value) + "]"
    if isinstance(value, Mapping):
        return "{" + ", ".join(f"{_key(k)} = {_value(v)}" for k, v in value.items()) + "}" if value else "{}"
    raise ElectionError(f"cannot write {type(value).__name__} to TOML")


def _table_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, Mapping) for item in value)


def to_toml(config: Mapping[str, Any]) -> str:
    """Scalars first, then ``[table]`` / ``[groups.<id>]`` blocks, then ``[[arrays]]``."""
    lines: list[str] = []
    for key, value in config.items():
        if not isinstance(value, Mapping) and not _table_list(value):
            lines.append(f"{_key(key)} = {_value(value)}")
    for key, value in config.items():
        if not isinstance(value, Mapping):
            continue
        if key == "groups":
            for gid, group in value.items():
                lines += ["", f"[groups.{_key(gid)}]"]
                lines += [f"{_key(k)} = {_value(v)}" for k, v in group.items()]
        else:
            lines += ["", f"[{_key(key)}]"]
            lines += [f"{_key(k)} = {_value(v)}" for k, v in value.items()]
    for key, value in config.items():
        if _table_list(value):
            for item in value:
                lines += ["", f"[[{_key(key)}]]"]
                lines += [f"{_key(k)} = {_value(v)}" for k, v in item.items()]
    return "\n".join(lines).lstrip("\n") + "\n"
