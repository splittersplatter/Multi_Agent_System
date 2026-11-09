"""Run or resume the current honest baseline."""

import argparse
import csv
from datetime import datetime, timezone
import gzip
import json
import sys
import tomllib
from pathlib import Path
import re
from .engine import Simulation
from .experiments import batch, compare_heuristics, compare_proximity, coalition_ablations, compare_campaign_policies, exhaustive_one_round_campaign, compare_signal_responses, compare_nominations, compare_alignment, calibrate_and_evaluate_detector, compare_leaders
from .metrics import frame_metrics, series
from .model import ElectionError, make_scenario
from .population import require_simulation_population
from .voting import VOTING_POLICIES, COALITION_POLICIES, SIGNAL_POLICIES, STRATEGIC, configure_voting
from .epistemic import EPISTEMIC_POLICIES
from .combined import combined_ablation
from .state_recording import RecordingGroup, active_recordings


from .exports import (write_jsonl as _write_jsonl, preflight_outputs as _preflight_outputs,
                      write_metrics_csv as _write_metrics_csv)


def _comparison_plots(result, directory):
    """Save one labelled vote-share plot per available recorded run."""
    from .render import export_metric_plot
    tracks = []
    def visit(value, path):
        if isinstance(value, dict):
            metrics = value.get("metrics")
            if (isinstance(metrics, list) and metrics and isinstance(metrics[0], dict)
                    and isinstance(metrics[0].get("shares"), dict) and "round" in metrics[0]):
                tracks.append((path, metrics))
            for key, item in value.items():
                if key not in ("metrics", "frames", "scenario"):
                    visit(item, (*path, str(key)))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, (*path, str(index)))
    visit(result, ())
    if not tracks:
        raise ElectionError("no recorded vote-share trajectories available for plotting; result retained")
    directory.mkdir()
    manifest = []
    for index, (label, rows) in enumerate(tracks, 1):
        name = re.sub(r"[^a-zA-Z0-9_-]+", "-", "-".join(label))[-100:] or "run"
        path = directory / f"{index:04d}-{name}.svg"
        export_metric_plot(tuple(rows[0]["shares"]), rows, path)
        manifest.append({"path": path.name, "result_location": label})
    with (directory / "index.json").open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2); handle.write("\n")
    print(f"Saved {len(manifest)} plots: {directory}", file=sys.stderr)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    majority = commands.add_parser("estimate-majority", help="passive matched majority-estimator pilot; no voting changes")
    majority.add_argument("scenario", type=Path, nargs="?", help="TOML scenario; omit with --pilot")
    majority.add_argument("--pilot", action="store_true", help="30 built-in trajectories at default seeds")
    majority.add_argument("--seeds", type=int, nargs="+", default=[101, 102, 103, 104, 105])
    majority.add_argument("--sensitivity", action="store_true", help="add window 5/20 and weight .25/.75 controls")
    majority.add_argument("--output-dir", type=Path, help="new artifact directory; defaults to timestamped outputs directory")
    run = commands.add_parser("run", help="run a TOML scenario")
    run.add_argument("scenario", type=Path)
    run.add_argument("--checkpoint", type=Path, help="write final JSON checkpoint")
    recording = run.add_mutually_exclusive_group()
    recording.add_argument("--summary", action="store_true", help="stream metrics without retaining frames")
    recording.add_argument("--sample", type=int, metavar="STRIDE", help="output every STRIDE frames plus the final frame")
    run.add_argument("--jsonl", type=Path, help="write manifest, metrics and recorded frames as JSONL")
    run.add_argument("--until-equilibrium", action="store_true", help="stop a certified case at its proven equilibrium, up to the scenario round limit")
    frequencies = commands.add_parser("frequencies", help="stream fixed-horizon occupation/phase diagnostics; no stationarity claim")
    frequencies.add_argument("scenario", type=Path)
    frequencies.add_argument("--rounds", type=int, default=10000)
    frequencies.add_argument("--burn-in", type=int, default=1000, help="fixed excluded prefix; not validated mixing time")
    frequencies.add_argument("--batch-size", type=int, default=100)
    frequencies.add_argument("--rows", type=Path, help="exclusive raw per-round CSV; existing parent required")
    frequencies.add_argument("--output", type=Path, help="exclusive summary JSON; stdout if omitted when --rows is supplied")
    frequencies.add_argument("--control", choices=("baseline", "sincere"), default="baseline")
    frequencies.add_argument("--seed", type=int, help="explicit episode seed; default scenario seed")
    resume = commands.add_parser("resume", help="verify and resume a JSON checkpoint")
    resume.add_argument("checkpoint", type=Path)
    resume.add_argument("--rounds", type=int, required=True, help="additional rounds")
    resume.add_argument("--until-equilibrium", action="store_true", help="stop a certified case at its proven equilibrium, up to --rounds")
    resume.add_argument("--output", type=Path, help="write resumed JSON checkpoint")
    resume.add_argument("--allow-environment-change", action="store_true", help="replay and migrate after reviewing runtime/core changes")
    batches = commands.add_parser("batch", help="compare scheduled edits with a matched control")
    batches.add_argument("scenario", type=Path)
    batches.add_argument("--seeds", type=int, nargs="+", required=True)
    batches.add_argument("--target", required=True)
    batches.add_argument("--csv", type=Path)
    batches.add_argument("--plot-svg", type=Path)
    batches.add_argument("--plot-png", type=Path)
    batches.add_argument("--output", type=Path, help="save complete batch JSON")
    export = commands.add_parser("export", help="export checkpoint metrics as CSV")
    export.add_argument("checkpoint", type=Path)
    export.add_argument("--csv", type=Path)
    export.add_argument("--plot-svg", type=Path)
    export.add_argument("--plot-png", type=Path)
    export.add_argument("--network-png", type=Path)
    export.add_argument("--gif", type=Path)
    export.add_argument("--frame", type=int, default=-1, help="network frame index; defaults to latest")
    export.add_argument("--stride", type=int, default=1)
    export.add_argument("--fps", type=int, default=5)
    export.add_argument("--allow-environment-change", action="store_true", help="replay after reviewing runtime/core changes")
    visual = commands.add_parser("visual", help="open a local interactive session")
    visual.add_argument("scenario", type=Path)
    visual.add_argument("--port", type=int, default=8000)
    view = commands.add_parser("view", help="browse a saved round-state JSONL timeline without rerunning policies")
    view.add_argument("states", type=Path, nargs="?", help="saved --save-states JSONL file")
    view.add_argument("--latest", action="store_true", help="open the most recently modified state recording in outputs/")
    view.add_argument("--port", type=int, default=8000)
    compare = commands.add_parser("compare", help="matched-seed voting heuristic comparison; stdout JSON")
    compare.add_argument("scenario", type=Path)
    compare.add_argument("--seeds", type=int, nargs="+", required=True)
    compare.add_argument("--policies", nargs="+", choices=VOTING_POLICIES + EPISTEMIC_POLICIES, default=["sincere","sensed_plurality",*STRATEGIC])
    compare.add_argument("--parameters", default="{}", help="JSON strategic parameters shared across policies")
    compare.add_argument("--rounds", type=int)
    compare.add_argument("--window", type=int, default=10)
    compare.add_argument("--output", type=Path, help="new JSON output file; never overwrite")
    networks = commands.add_parser("compare-networks", help="paired dynamic versus frozen-initial proximity; stdout JSON")
    networks.add_argument("scenario", type=Path)
    networks.add_argument("--seeds", type=int, nargs="+", required=True)
    networks.add_argument("--calibration-seeds", type=int, nargs="+", help="disjoint one-to-one seeds for the optional static exposure control")
    networks.add_argument("--output", type=Path, help="new JSON output file; never overwrite")
    ablations = commands.add_parser("coalition-ablations", help="matched coalition capability ablations; stdout JSON")
    ablations.add_argument("scenario", type=Path)
    ablations.add_argument("--seeds", type=int, nargs="+", required=True)
    ablations.add_argument("--output", type=Path, help="new JSON output file; never overwrite")
    campaign = commands.add_parser("compare-campaign", help="matched campaign-controller policy comparisons; stdout JSON")
    campaign.add_argument("scenario", type=Path)
    campaign.add_argument("--seeds", type=int, nargs="+", required=True)
    campaign.add_argument("--output", type=Path, help="new JSON output file; never overwrite")
    signals = commands.add_parser("compare-signals", help="paired truthful and distorted signals across voter responses; stdout JSON")
    signals.add_argument("scenario", type=Path)
    signals.add_argument("--seeds", type=int, nargs="+", required=True)
    signals.add_argument("--groups", nargs="+", required=True, help="occupied groups whose voter response is compared")
    signals.add_argument("--signal-distortion-bound", type=int, required=True, help="declared epistemic transfer bound")
    signals.add_argument("--max-worlds", type=int, default=10000)
    signals.add_argument("--output", type=Path, help="new JSON output file; never overwrite")
    nominations = commands.add_parser("compare-nominations", help="paired endogenous, identical fixed and random nominee controls")
    nominations.add_argument("scenario", type=Path)
    nominations.add_argument("--seeds", type=int, nargs="+", required=True)
    nominations.add_argument("--output", type=Path, help="new JSON output file; never overwrite")
    alignments = commands.add_parser("compare-alignment", help="paired drift and bounded alignment attack controls")
    alignments.add_argument("scenario", type=Path)
    alignments.add_argument("--seeds", type=int, nargs="+", required=True)
    alignments.add_argument("--output", type=Path, help="new JSON output file; never overwrite")
    detector = commands.add_parser("evaluate-detector", help="calibrate on no-alignment-attack seeds, then evaluate on disjoint seeds")
    detector.add_argument("scenario", type=Path)
    detector.add_argument("--calibration-seeds", type=int, nargs="+", required=True)
    detector.add_argument("--evaluation-seeds", type=int, nargs="+", required=True)
    detector.add_argument("--false-alarm-rate", type=float, required=True)
    detector.add_argument("--output", type=Path, help="new JSON output file; never overwrite")
    leaders = commands.add_parser("compare-leaders", help="paired fixed/adaptive leaders with broadcast/frozen perceptions")
    leaders.add_argument("scenario", type=Path)
    leaders.add_argument("--seeds", type=int, nargs="+", required=True)
    leaders.add_argument("--output", type=Path, help="new JSON output file; never overwrite")
    combined = commands.add_parser("combined-ablation", help="versioned seven-mechanism isolated and leave-one-out controls")
    combined.add_argument("scenario", type=Path)
    combined.add_argument("--seeds", type=int, nargs="+", required=True)
    combined.add_argument("--target", required=True)
    combined.add_argument("--output", type=Path, help="new JSON output file; never overwrite")
    exhaustive = commands.add_parser("campaign-exhaustive", help="exact evaluator-only one-round campaign bounds; stdout JSON")
    exhaustive.add_argument("scenario", type=Path)
    exhaustive.add_argument("--max-combinations", type=int, default=10000)
    exhaustive.add_argument("--output", type=Path, help="new JSON output file; never overwrite")
    knowledge = commands.add_parser("knowledge", help="analyze an explicitly specified finite knowledge model")
    knowledge.add_argument("model", type=Path, help="JSON possible-world model")
    knowledge.add_argument("--agent", help="agent for possible-world manipulation analysis")
    knowledge.add_argument("--world", help="analyze another named world; default is actual")
    knowledge.add_argument("--max-worlds", type=int, default=10000)
    conditional = knowledge.add_mutually_exclusive_group()
    conditional.add_argument("--conditional", type=Path, help="JSON conditional first-choice profile to check")
    conditional.add_argument("--solve-conditional", action="store_true", help="enumerate all conditional equilibria within limits")
    knowledge.add_argument("--max-profiles", type=int, default=10000)
    knowledge.add_argument("--max-evaluations", type=int, default=1000000)
    for command in (run, batches, visual):
        command.add_argument("--voting", choices=VOTING_POLICIES + COALITION_POLICIES + SIGNAL_POLICIES + EPISTEMIC_POLICIES, help="episode-wide voting policy; preserves movement and permissions")
        command.add_argument("--voting-parameters", default="{}", help="JSON parameters for selected voting policy")
    for command in (run, resume, frequencies, batches, visual, majority, compare, networks, ablations, campaign,
                    signals, nominations, alignments, detector, leaders, combined):
        command.add_argument("--save-plots", action="store_true", help="save a timestamped SVG plot in outputs/")
        command.add_argument("--save-states", action="store_true", help="stream every committed round to timestamped JSONL for browser playback")
    args = parser.parse_args(argv)
    recording_group, recording_token = None, None
    try:
        if args.command == "view":
            from .playback import make_playback_server
            if args.latest == (args.states is not None):
                raise ElectionError("provide a state recording or --latest")
            if args.latest:
                candidates = list(Path("outputs").glob("*-states*.jsonl"))
                if not candidates:
                    raise ElectionError("no state recordings found in outputs/; run a simulation with --save-states first")
                args.states = max(candidates, key=lambda path: (path.stat().st_mtime_ns, path.name))
            if not 0 <= args.port <= 65535:
                raise ElectionError("port must be between 0 and 65535")
            server = make_playback_server(args.states, args.port)
            print(f"Viewing states: {args.states}", flush=True)
            print(f"Open http://127.0.0.1:{server.server_port}/ (recorded playback; Ctrl-C to stop)", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
            return 0
        simulation_commands = {"run", "resume", "visual", "frequencies", "batch", "estimate-majority",
                               "compare", "compare-networks", "coalition-ablations", "compare-campaign",
                               "compare-signals", "compare-nominations", "compare-alignment",
                               "evaluate-detector", "compare-leaders", "combined-ablation"}
        auto_base = None
        automatic_comparison = False
        if args.command in simulation_commands:
            output_dir = Path("outputs")
            output_dir.mkdir(exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S-%fZ")
            auto_base = output_dir / f"{args.command}-{timestamp}"
            if args.command == "estimate-majority" and args.output_dir is None:
                args.output_dir = auto_base
            elif args.command in simulation_commands - {"run", "resume", "visual", "frequencies", "batch", "estimate-majority"} and args.output is None:
                args.output = auto_base.with_suffix(".json")
                automatic_comparison = True
            elif args.command == "batch" and args.output is None:
                args.output = auto_base.with_suffix(".json")
            elif args.command == "resume" and args.output is None:
                args.output = auto_base.with_suffix(".json")
            elif args.command == "run" and args.checkpoint is None and args.jsonl is None:
                if args.summary or args.sample is not None:
                    args.jsonl = auto_base.with_suffix(".jsonl")
                else:
                    args.checkpoint = auto_base.with_suffix(".json")
            if getattr(args, "save_states", False):
                prefix = auto_base.with_name(auto_base.name + "-states")
                _preflight_outputs([prefix.with_name(prefix.name + ".jsonl")])
                recording_group = RecordingGroup(prefix)
                recording_token = active_recordings.set(recording_group)
        plot_path = auto_base.with_suffix(".svg") if auto_base is not None and getattr(args, "save_plots", False) else None
        comparison_commands = {"compare", "compare-networks", "coalition-ablations", "compare-campaign",
                               "compare-signals", "compare-nominations", "compare-alignment", "evaluate-detector",
                               "compare-leaders", "combined-ablation"}
        plot_directory = auto_base.with_name(auto_base.name + "-plots") if args.command in comparison_commands and plot_path else None
        if plot_directory is not None:
            _preflight_outputs([plot_directory])
        def save_comparison_plots(result):
            if plot_directory is not None:
                _comparison_plots(result, plot_directory)
            if automatic_comparison:
                print(f"Saved comparison: {args.output}", file=sys.stderr)
                print(json.dumps(result, indent=2, allow_nan=False))
                return True
            return False
        if args.command == "frequencies":
            from .occupation import run_frequencies, configure_control
            if args.rows is None and args.output is None:
                args.rows = auto_base.with_suffix(".csv")
                args.output = auto_base.with_suffix(".json")
            if plot_path is not None and args.rows is None:
                args.rows = auto_base.with_suffix(".csv")
            _preflight_outputs([args.rows, args.output, plot_path])
            with args.scenario.open("rb") as handle:
                frequency_raw = tomllib.load(handle)
            if args.seed is not None:
                frequency_raw["seed"] = args.seed
            frequency_scenario = configure_control(make_scenario(frequency_raw), args.control)
            result = run_frequencies(frequency_scenario, rounds=args.rounds, burn_in=args.burn_in,
                                     batch_size=args.batch_size, rows_path=args.rows)
            result["control"] = args.control
            if plot_path is not None and result["completed_rounds"]:
                from .render import export_metric_plot
                with args.rows.open(encoding="utf-8", newline="") as handle:
                    rows = [{"round": int(row["round"]), "shares": {p: float(row[f"share:{p}"]) for p in frequency_scenario.parties}}
                            for row in csv.DictReader(handle)]
                export_metric_plot(frequency_scenario.parties, rows, plot_path)
            if args.output:
                with args.output.open("x", encoding="utf-8") as handle:
                    json.dump(result, handle, indent=2, allow_nan=False)
                    handle.write("\n")
                print(json.dumps({"output": str(args.output), "rows": str(args.rows) if args.rows else None, "plot": str(plot_path) if plot_path and plot_path.exists() else None, "status": result["status"],
                                  "completed_rounds": result["completed_rounds"]}))
            else:
                print(json.dumps(result, indent=2, allow_nan=False))
            return 0 if result["status"] == "complete" else 1
        if args.command == "estimate-majority":
            from .majority_experiments import run_pilot
            if args.pilot == (args.scenario is not None):
                raise ElectionError("provide either a scenario or --pilot")
            scenario = None
            if args.scenario is not None:
                with args.scenario.open("rb") as handle:
                    scenario = make_scenario(tomllib.load(handle))
            result = run_pilot(args.output_dir, seeds=args.seeds, sensitivity=args.sensitivity, scenario=scenario)
            if args.save_plots:
                from .render import export_metric_plot
                plotted = 0
                for run in result["runs"]:
                    if run["status"] != "ok":
                        continue
                    folder = args.output_dir / run["name"]
                    with gzip.open(folder / "predictions.jsonl.gz", "rt", encoding="utf-8") as handle:
                        header = json.loads(next(handle))
                        parties, rows, last_round = header["parties"], [], None
                        for line in handle:
                            row = json.loads(line)
                            if row["round"] == last_round:
                                continue
                            counts = row["truth_counts"]
                            total = sum(counts.values())
                            rows.append({"round": row["source_round"], "shares": {p: counts[p] / total for p in parties}})
                            last_round = row["round"]
                    if rows:
                        export_metric_plot(parties, rows, folder / "vote-shares.svg")
                        plotted += 1
                if not plotted:
                    raise ElectionError(f"no completed pilot trajectories available for plots; results retained at {args.output_dir}")
            print(json.dumps({"output_dir": str(args.output_dir), "runs": len(result["runs"]), "failed": result["failed"]}))
            return 1 if result["failed"] else 0
        if args.command == "knowledge":
            from .epistemic import KnowledgeModel
            with args.model.open(encoding="utf-8") as handle:
                model = KnowledgeModel.from_dict(json.load(handle), max_worlds=args.max_worlds)
            if args.conditional or args.solve_conditional:
                if args.agent is not None or args.world is not None:
                    raise ElectionError("conditional analysis covers all agents and worlds; omit --agent and --world")
                if args.conditional:
                    with args.conditional.open(encoding="utf-8") as handle:
                        analysis = model.conditional_equilibrium(json.load(handle), max_evaluations=args.max_evaluations)
                else:
                    analysis = model.solve_conditional_equilibria(max_profiles=args.max_profiles,
                                                                  max_evaluations=args.max_evaluations)
                print(json.dumps({"record_type":"eclipse.conditional-equilibrium", "record_version":1,
                                  "actual_world":model.actual, "analysis":analysis}, indent=2, allow_nan=False))
                return 0
            if args.agent is None:
                raise ElectionError("knowledge analysis requires --agent or a conditional mode")
            print(json.dumps({"record_type":"eclipse.knowledge-analysis", "record_version":1,
                              "actual_world":model.actual, "analysis_world":args.world or model.actual,
                              "analysis":model.analyze(args.agent, args.world)}, indent=2, allow_nan=False))
            return 0
        if args.command in ("run", "batch", "visual", "compare", "compare-networks", "coalition-ablations", "compare-campaign", "campaign-exhaustive", "compare-signals", "compare-nominations", "compare-alignment", "evaluate-detector", "compare-leaders", "combined-ablation"):
            with args.scenario.open("rb") as handle:
                scenario = make_scenario(tomllib.load(handle))
            require_simulation_population(scenario)
            if args.command == "combined-ablation":
                _preflight_outputs([args.output])
                result = combined_ablation(scenario, args.seeds, args.target)
                if args.output:
                    with args.output.open("x", encoding="utf-8") as handle:
                        json.dump(result, handle, indent=2, allow_nan=False); handle.write("\n")
                    if save_comparison_plots(result):
                        return 0
                    runs = [run for row in result["rows"] for run in row["runs"].values()]
                    print(json.dumps({"output": str(args.output), "seeds": len(result["rows"]), "arms_per_seed": len(result["arms"]),
                                      "failed": sum(run["status"] != "ok" or run.get("movement_matched") is False or run.get("same_candidates") is False for run in runs),
                                      "unpaired": sum(run["status"] == "ok" and "paired" not in run for run in runs),
                                      "detector_invariant_failures": sum(run.get("detector_noninterference") is False for run in runs)}))
                else:
                    print(json.dumps(result, indent=2, allow_nan=False))
                return 0
            if args.command == "compare-leaders":
                _preflight_outputs([args.output])
                result = compare_leaders(scenario, args.seeds)
                if args.output:
                    with args.output.open("x", encoding="utf-8") as handle:
                        json.dump(result, handle, indent=2, allow_nan=False); handle.write("\n")
                    if save_comparison_plots(result):
                        return 0
                    runs = [run for row in result["rows"] for run in row["runs"].values()]
                    print(json.dumps({"output": str(args.output), "seeds": len(result["rows"]),
                                      "failed": sum(run["status"] != "ok" or run.get("movement_matched") is False for run in runs),
                                      "unpaired": sum(run["status"] == "ok" and "paired" not in run for run in runs),
                                      "invariant_failures": sum(run.get("nonsignal_invariant") is False for run in runs)}))
                else:
                    print(json.dumps(result, indent=2, allow_nan=False))
                return 0
            if args.command == "evaluate-detector":
                _preflight_outputs([args.output])
                result = calibrate_and_evaluate_detector(scenario, args.calibration_seeds, args.evaluation_seeds, args.false_alarm_rate)
                if args.output:
                    with args.output.open("x", encoding="utf-8") as handle:
                        json.dump(result, handle, indent=2, allow_nan=False); handle.write("\n")
                    if save_comparison_plots(result):
                        return 0
                    print(json.dumps({"output": str(args.output), "status": result["status"], "threshold": result["threshold"],
                                      "calibration_failed": sum(r["status"] != "ok" for r in result["calibration"]),
                                      "evaluation_failures": None if result["evaluation"] is None else
                                      sum(run["status"] != "ok" for row in result["evaluation"]["rows"] for run in row["runs"].values()),
                                      "evaluation_unpaired": None if result["evaluation"] is None else
                                      sum(run["status"] == "ok" and "paired" not in run for row in result["evaluation"]["rows"] for run in row["runs"].values())}))
                else:
                    print(json.dumps(result, indent=2, allow_nan=False))
                return 0
            if args.command == "compare-alignment":
                _preflight_outputs([args.output])
                result = compare_alignment(scenario, args.seeds)
                if args.output:
                    with args.output.open("x", encoding="utf-8") as handle:
                        json.dump(result, handle, indent=2, allow_nan=False); handle.write("\n")
                    if save_comparison_plots(result):
                        return 0
                    runs = [run for row in result["rows"] for run in row["runs"].values()]
                    print(json.dumps({"output": str(args.output), "seeds": len(result["rows"]),
                                      "failed": sum(run["status"] != "ok" or run.get("movement_matched") is False for run in runs),
                                      "unpaired": sum(run["status"] == "ok" and "paired" not in run for run in runs)}))
                else:
                    print(json.dumps(result, indent=2, allow_nan=False))
                return 0
            if args.command == "compare-nominations":
                _preflight_outputs([args.output])
                result = compare_nominations(scenario, args.seeds)
                if args.output:
                    with args.output.open("x", encoding="utf-8") as handle:
                        json.dump(result, handle, indent=2, allow_nan=False); handle.write("\n")
                    if save_comparison_plots(result):
                        return 0
                    runs = [run for row in result["rows"] for run in row["runs"].values()]
                    print(json.dumps({"output": str(args.output), "seeds": len(result["rows"]),
                                      "failed": sum(run["status"] != "ok" or run.get("movement_matched") is False for run in runs),
                                      "unpaired": sum(run["status"] == "ok" and "paired" not in run for run in runs)}))
                else:
                    print(json.dumps(result, indent=2, allow_nan=False))
                return 0
            if args.command == "compare-signals":
                _preflight_outputs([args.output])
                result = compare_signal_responses(scenario, args.seeds, args.groups, args.signal_distortion_bound, args.max_worlds)
                if args.output:
                    with args.output.open("x", encoding="utf-8") as handle:
                        json.dump(result, handle, indent=2, allow_nan=False); handle.write("\n")
                    if save_comparison_plots(result):
                        return 0
                    runs = [run for row in result["rows"] for response in row["runs"].values() for run in response.values()]
                    print(json.dumps({"output": str(args.output), "seeds": len(result["rows"]),
                                      "failed": sum(run["status"] != "ok" or run.get("movement_matched") is False
                                                    or run.get("response_movement_matched") is False for run in runs),
                                      "unpaired": sum(run["status"] == "ok" and "paired" not in run for run in runs),
                                      "response_unpaired": sum(run["status"] == "ok" and "response_paired" not in run for run in runs)}))
                else:
                    print(json.dumps(result, indent=2, allow_nan=False))
                return 0
            if args.command == "campaign-exhaustive":
                _preflight_outputs([args.output])
                result = exhaustive_one_round_campaign(scenario,args.max_combinations)
                if args.output:
                    with args.output.open("x",encoding="utf-8") as handle:
                        json.dump(result,handle,indent=2,allow_nan=False); handle.write("\n")
                    print(json.dumps({"output":str(args.output),"combinations_checked":result["combinations_checked"]}))
                else:
                    print(json.dumps(result,indent=2,allow_nan=False))
                return 0
            if args.command == "compare-campaign":
                _preflight_outputs([args.output])
                result = compare_campaign_policies(scenario,args.seeds)
                if args.output:
                    with args.output.open("x",encoding="utf-8") as handle:
                        json.dump(result,handle,indent=2,allow_nan=False); handle.write("\n")
                    if save_comparison_plots(result):
                        return 0
                    print(json.dumps({"output":str(args.output),"seeds":len(result["rows"]),
                                      "failed":sum(run["status"] != "ok" or run.get("movement_matched") is False
                                                   for row in result["rows"] for run in row["runs"].values()),
                                      "unpaired":sum(run["status"] == "ok" and "paired" not in run
                                                     for row in result["rows"] for run in row["runs"].values())}))
                else:
                    print(json.dumps(result,indent=2,allow_nan=False))
                return 0
            if args.command == "coalition-ablations":
                _preflight_outputs([args.output])
                result = coalition_ablations(scenario,args.seeds)
                if args.output:
                    with args.output.open("x",encoding="utf-8") as handle:
                        json.dump(result,handle,indent=2,allow_nan=False); handle.write("\n")
                    if save_comparison_plots(result):
                        return 0
                    print(json.dumps({"output":str(args.output),"seeds":len(result["rows"]),
                                      "failed":sum(run["status"] != "ok" or run.get("movement_matched") is False
                                                   for row in result["rows"] for run in row["runs"].values()),
                                      "unpaired":sum(run["status"] == "ok" and "paired_targets" not in run
                                                     for row in result["rows"] for run in row["runs"].values())}))
                else:
                    print(json.dumps(result,indent=2,allow_nan=False))
                return 0
            if args.command == "compare-networks":
                _preflight_outputs([args.output])
                result = compare_proximity(scenario, args.seeds, args.calibration_seeds)
                if args.output:
                    with args.output.open("x", encoding="utf-8") as handle:
                        json.dump(result,handle,indent=2,allow_nan=False); handle.write("\n")
                    if save_comparison_plots(result):
                        return 0
                    print(json.dumps({"output":str(args.output),"pairs":len(result["rows"]),
                                      "failed":sum(row["status"] != "ok" for row in result["rows"]),
                                      "matched_failed":sum(row["matched_static"]["status"] in ("failed", "movement_mismatch") for row in result["rows"])}))
                else:
                    print(json.dumps(result,indent=2,allow_nan=False))
                return 0
            if args.command == "compare":
                _preflight_outputs([args.output])
                result=compare_heuristics(scenario,args.seeds,args.policies,json.loads(args.parameters),args.rounds,args.window)
                if args.output:
                    with args.output.open("x",encoding="utf-8") as handle:
                        json.dump(result,handle,indent=2,allow_nan=False);handle.write("\n")
                    if save_comparison_plots(result):
                        return 0
                    print(json.dumps({"output":str(args.output),"runs":len(result["rows"]),
                                      "failed":sum(r["status"]=="failed" for r in result["rows"])}))
                else:
                    print(json.dumps(result,indent=2,allow_nan=False))
                return 0
            if args.voting:
                scenario = configure_voting(scenario, args.voting, json.loads(args.voting_parameters))
            elif args.voting_parameters != "{}":
                raise ElectionError("--voting-parameters requires --voting")
            if args.command == "batch":
                _preflight_outputs([args.csv, args.plot_svg, args.plot_png, args.output, plot_path])
                if args.plot_png:
                    from .render import _pillow
                    _pillow()
                result = batch(scenario, args.seeds, args.target)
                with args.output.open("x", encoding="utf-8") as handle:
                    json.dump(result, handle, indent=2, allow_nan=False); handle.write("\n")
                if plot_path:
                    from .render import export_comparison
                    export_comparison(result, plot_path, "svg")
                print(f"Saved batch: {args.output}" + (f"; plot: {plot_path}" if plot_path else ""), file=sys.stderr)
                if args.csv:
                    with args.csv.open("x", encoding="utf-8", newline="") as handle:
                        writer = csv.writer(handle)
                        writer.writerow(["seed", "round", "control_winner", "treated_winner", "control_target_share", "treated_target_share", "target_share_delta"])
                        for row in result["rows"]:
                            for control, treated in zip(row["control"], row["treated"]):
                                left, right = control["shares"][args.target], treated["shares"][args.target]
                                writer.writerow([row["seed"], control["round"], control["winner"], treated["winner"], left, right, right-left])
                if args.plot_svg or args.plot_png:
                    from .render import export_comparison
                    if args.plot_svg: export_comparison(result, args.plot_svg, "svg")
                    if args.plot_png: export_comparison(result, args.plot_png, "png")
                print(json.dumps(result, indent=2))
                return 0
            if args.command == "visual":
                from .visual import make_server
                if not 0 <= args.port <= 65535:
                    raise ElectionError("port must be between 0 and 65535")
                simulation = Simulation(scenario)
                visual_checkpoint = auto_base.with_suffix(".json")
                _preflight_outputs([visual_checkpoint, plot_path])
                server = make_server(simulation, args.port)
                print(f"Open http://127.0.0.1:{server.server_port}/ (Ctrl-C to stop)", flush=True)
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    pass
                finally:
                    server.server_close()
                    with server.session.lock:
                        simulation = server.session.simulation
                        with visual_checkpoint.open("x", encoding="utf-8") as handle:
                            json.dump(simulation.checkpoint(), handle, indent=2, allow_nan=False); handle.write("\n")
                        if plot_path:
                            from .render import export_plot
                            export_plot(simulation.scenario, simulation.frames, plot_path, "svg")
                    print(f"Saved checkpoint: {visual_checkpoint}" + (f"; plot: {plot_path}" if plot_path else ""), flush=True)
                return 0
            if args.sample is not None and args.sample < 1:
                raise ElectionError("sample stride must be a positive integer")
            if args.summary and args.checkpoint:
                raise ElectionError("summary recording cannot write a full-history checkpoint")
            _preflight_outputs([args.checkpoint, args.jsonl, plot_path])
            simulation = Simulation(scenario)
            if args.until_equilibrium and not scenario.convergence_case:
                raise ElectionError("--until-equilibrium requires a certified convergence scenario")
            if args.summary or (args.sample is not None and args.checkpoint is None):
                if args.checkpoint:
                    raise ElectionError("summary recording cannot write a full-history checkpoint")
                measured = [frame_metrics(scenario, simulation.current)]
                samples = [simulation.current.as_dict()] if args.sample is not None else []
                for _ in range(scenario.rounds):
                    if args.until_equilibrium and measured[-1]["convergence"]["status"] in ("certified_equilibrium", "certified_policy_equilibrium"):
                        break
                    previous = simulation.current
                    current = simulation.step()
                    measured.append(frame_metrics(scenario, current, previous))
                    if args.sample is not None and (current.round % args.sample == 0 or current.round == scenario.rounds):
                        samples.append(current.as_dict())
                    simulation.frames = [current]
                if args.sample is not None and samples[-1]["round"] != simulation.current.round:
                    samples.append(simulation.current.as_dict())
                output_data = {"record_type": "eclipse.run", "record_version": 2,
                               "seed": scenario.seed, "parties": scenario.parties, "k": scenario.k,
                               "scenario": scenario.as_dict(), "manifest": simulation.runtime_manifest,
                               "policy_digests": {name: digest for name, (_, digest, _) in simulation.plugins.items()},
                               "recording": "summary" if args.summary else "sampled", "metrics": measured}
                if scenario.nomination is not None:
                    output_data["nomination"] = scenario.nomination.as_dict()
                if args.sample is not None:
                    output_data.update({"stride": args.sample, "frames": samples})
                if args.jsonl:
                    _write_jsonl(args.jsonl, output_data)
                    print(f"Saved recording: {args.jsonl}", file=sys.stderr)
                if plot_path:
                    from .render import export_metric_plot
                    export_metric_plot(scenario.parties, measured, plot_path)
                    print(f"Saved plot: {plot_path}", file=sys.stderr)
                print(json.dumps(output_data, indent=2))
                return 0
            if args.until_equilibrium:
                for _ in range(scenario.rounds):
                    if frame_metrics(scenario, simulation.current)["convergence"]["status"] in ("certified_equilibrium", "certified_policy_equilibrium"):
                        break
                    simulation.step()
            else:
                simulation.run()
            output = args.checkpoint
        elif args.command == "resume":
            _preflight_outputs([args.output, plot_path])
            with args.checkpoint.open(encoding="utf-8") as handle:
                simulation = Simulation.from_checkpoint(json.load(handle), allow_environment_change=args.allow_environment_change)
            if args.until_equilibrium:
                if not simulation.scenario.convergence_case:
                    raise ElectionError("--until-equilibrium requires a certified convergence scenario")
                if args.rounds < 0:
                    raise ElectionError("rounds must be a non-negative integer")
                for _ in range(args.rounds):
                    if frame_metrics(simulation.scenario, simulation.current)["convergence"]["status"] in ("certified_equilibrium", "certified_policy_equilibrium"):
                        break
                    simulation.step()
            else:
                simulation.run(args.rounds)
            scenario = simulation.scenario
            output = args.output
        else:
            with args.checkpoint.open(encoding="utf-8") as handle:
                simulation = Simulation.from_checkpoint(json.load(handle), allow_environment_change=args.allow_environment_change)
            rows = series(simulation.scenario, simulation.frames)
            outputs = [args.csv, args.plot_svg, args.plot_png, args.network_png, args.gif]
            if not any(outputs):
                raise ElectionError("choose at least one export option")
            if not -len(simulation.frames) <= args.frame < len(simulation.frames):
                raise ElectionError("frame index is out of range")
            if args.stride < 1 or not 1 <= args.fps <= 100:
                raise ElectionError("stride must be positive; fps must be 1..100")
            _preflight_outputs(outputs)
            if any((args.plot_png, args.network_png, args.gif)):
                from .render import _pillow
                _pillow()
            if args.csv:
                _write_metrics_csv(args.csv, simulation.scenario, rows)
            if any((args.plot_svg, args.plot_png, args.network_png, args.gif)):
                from .render import export_gif, export_network, export_plot
                if args.plot_svg: export_plot(simulation.scenario, simulation.frames, args.plot_svg, "svg")
                if args.plot_png: export_plot(simulation.scenario, simulation.frames, args.plot_png, "png")
                if args.network_png: export_network(simulation.scenario, simulation.frames[args.frame], args.network_png)
                if args.gif: export_gif(simulation.scenario, simulation.frames, args.gif, args.stride, args.fps)
            print(json.dumps({"outputs": [str(p) for p in outputs if p is not None], "rows": len(rows)}))
            return 0
        if output:
            with output.open("x", encoding="utf-8") as handle:
                json.dump(simulation.checkpoint(), handle, indent=2, allow_nan=False)
                handle.write("\n")
            print(f"Saved checkpoint: {output}", file=sys.stderr)
        if plot_path:
            from .render import export_plot
            export_plot(scenario, simulation.frames, plot_path, "svg")
            print(f"Saved plot: {plot_path}", file=sys.stderr)
    except (OSError, json.JSONDecodeError, tomllib.TOMLDecodeError, ElectionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        if recording_token is not None:
            active_recordings.reset(recording_token)
        if recording_group is not None:
            recording_group.close()
            for recorder in recording_group.recorders:
                print(f"Saved states: {recorder.path}", file=sys.stderr)
    result = {"record_type": "eclipse.run", "record_version": 2,
              "seed": scenario.seed, "parties": scenario.parties, "k": scenario.k,
              "scenario": scenario.as_dict(), "manifest": simulation.runtime_manifest,
              "policy_digests": {name: digest for name, (_, digest, _) in simulation.plugins.items()},
              "recording": "full", "metrics": series(scenario, simulation.frames)}
    if scenario.nomination is not None:
        result["nomination"] = scenario.nomination.as_dict()
    frames = simulation.frames
    if args.command == "run" and args.sample is not None:
        frames = frames[::args.sample]
        if frames[-1] is not simulation.frames[-1]: frames.append(simulation.frames[-1])
        result.update({"recording": "sampled", "stride": args.sample})
    result["frames"] = [frame.as_dict() for frame in frames]
    if args.command == "run" and args.jsonl:
        try:
            _write_jsonl(args.jsonl, result)
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    print(json.dumps(result, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except OSError as exc:
        # Includes flush/close errors from recording cleanup after an early return.
        print(f"error saving states: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
