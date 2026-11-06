"""Local, explicitly configured voting policies and isolated observations."""

from dataclasses import dataclass
import hashlib
import importlib
import importlib.util
import inspect
import json
from pathlib import Path
import random
import sys
import threading
from typing import Any
from .model import ElectionError

_plugin_lock = threading.RLock()
_loaded_modules: dict[object, dict[Path, str]] = {}


def _import_policy_source(name: str):
    """Compile exact source bytes, bypassing potentially stale timestamp bytecode."""
    spec = importlib.util.find_spec(name)
    # Importing a parent package during discovery can itself import the policy.
    if name in sys.modules:
        raise ValueError("module was imported outside the policy loader; restart without pre-importing it")
    if spec is None or spec.origin is None or not spec.origin.endswith(".py") or spec.loader is None:
        raise ValueError("policy must be a readable Python source module")
    path = Path(spec.origin).resolve()
    source = path.read_bytes()
    digest = hashlib.sha256(source).hexdigest()
    code = compile(source, str(path), "exec", dont_inherit=True)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        exec(code, module.__dict__)
        if sys.modules.get(name) is not module:
            raise ValueError("policy replaced its module during import")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("policy source changed during import")
    except BaseException:
        if sys.modules.get(name) is module:
            del sys.modules[name]
        raise
    parent_name, _, child = name.rpartition(".")
    if parent_name:
        setattr(sys.modules[parent_name], child, module)
    return module, path, digest


@dataclass(frozen=True, slots=True)
class Observation:
    person: str
    round: int
    parties: tuple[str, ...]
    k: int
    own_preference: tuple[str, ...]
    own_position: tuple[float, float]
    messages: tuple[tuple[str, str, tuple[str, ...]], ...]
    own_previous_ballot: tuple[str, ...] = ()
    public_neighbors: tuple[str, ...] = ()
    own_channels: tuple[str, ...] = ()
    # (sender, source, completed_round, ballot); distinct from untrusted reports.
    sensed_ballots: tuple[tuple[str, str, int, tuple[str, ...]], ...] = ()


def canonical_json(value: Any, label: str) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ElectionError(f"{label} must be JSON-serializable and finite") from exc


def policy_rng(seed: int, person: str, round_number: int, phase: str = "voting") -> random.Random:
    key = f"{seed}\0{phase}\0{len(person)}:{person}\0{round_number}".encode()
    return random.Random(int.from_bytes(hashlib.sha256(key).digest(), "big"))


def load_plugin(reference: str) -> tuple[Any, str, Path]:
    """Load trusted local code, returning callable, source digest and source path."""
    parts = reference.split(":")
    if len(parts) != 3 or parts[0] != "python" or not all(part.isidentifier() for part in parts[1].split(".")) or not parts[2].isidentifier():
        raise ElectionError("plugin voting must be python:module:function")
    # Coordinate with Python's normal import machinery without holding the
    # global import lock while trusted module initialization executes.
    with _plugin_lock, importlib._bootstrap._ModuleLockManager(parts[1]):
        try:
            module = sys.modules.get(parts[1])
            if module is not None and module not in _loaded_modules:
                raise ValueError("module was imported outside the policy loader; restart without pre-importing it")
            if module is None:
                module, module_path, module_digest = _import_policy_source(parts[1])
                _loaded_modules[module] = {module_path: module_digest}
            recorded = _loaded_modules[module]
            # Check every previously loaded function source, not just this function:
            # another reference from the same cached module must not conceal changes.
            for loaded_path, loaded_digest in recorded.items():
                if hashlib.sha256(loaded_path.read_bytes()).hexdigest() != loaded_digest:
                    raise ValueError("cached policy source changed; restart the process")
            function = getattr(module, parts[2])
            if not callable(function):
                raise TypeError("policy is not callable")
            source = inspect.getsourcefile(function)
            if not source:
                raise ValueError("policy has no readable source file")
            path = Path(source).resolve()
            if path not in recorded:
                raise ValueError("policy function must be defined in the configured source module")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            recorded[path] = digest
        except Exception as exc:
            raise ElectionError(f"cannot load policy {reference!r}: {exc}") from exc
        return function, digest, path
