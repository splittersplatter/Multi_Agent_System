"""Run tiny CLI regression fixtures, explicitly NOT outcome simulations.

    PYTHONPATH=src python3 scripts/verify_fixture.py run examples/baseline.toml

No browser server: normal CLI/GUI requires >=100 people. Used by subprocess tests.
"""

import contextlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from multi_agent_election.cli import main as cli_main
from multi_agent_election.population import verification_scope


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] == "visual":
        raise SystemExit("verification fixture tool requires a non-visual CLI command")
    captured = io.StringIO()
    with verification_scope("explicit CLI regression fixture"), contextlib.redirect_stdout(captured):
        status = cli_main(args)
    output = captured.getvalue()
    if output:
        record = json.loads(output)
        record["verification_only"] = True
        print(json.dumps(record, allow_nan=False))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
