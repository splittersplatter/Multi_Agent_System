"""Production simulations require >=100 people; tiny formal fixtures are explicit."""

from contextlib import contextmanager
from contextvars import ContextVar

from .model import ElectionError

MIN_SIMULATION_PEOPLE = 100
_verification_reason = ContextVar("eclipse_verification_reason", default=None)


def current_verification_reason():
    return _verification_reason.get()


@contextmanager
def verification_scope(reason):
    """Only for unit tests/formal regression fixtures, never outcome studies.

    Explicit and scoped; no environment-variable/test-framework autodetection.
    Normal CLI/browser/experiment entrypoints never enable this exception.
    """
    if not isinstance(reason, str) or not reason.strip():
        raise ElectionError("verification scope requires a nonempty reason")
    token = _verification_reason.set(reason)
    try:
        yield
    finally:
        _verification_reason.reset(token)


def require_population(count):
    if type(count) is not int or count < 1:
        raise ElectionError("population must be a positive integer")
    if count < MIN_SIMULATION_PEOPLE and _verification_reason.get() is None:
        raise ElectionError(f"simulations require at least {MIN_SIMULATION_PEOPLE} people; got {count}. "
                            "Use a >=100-person scenario; tiny cases are verification fixtures only.")


def require_simulation_population(scenario):
    require_population(len(scenario.people))
