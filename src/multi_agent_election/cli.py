"""Run or resume the current honest baseline."""

import argparse
import csv
import json
import sys
import tomllib
from pathlib import Path
from .engine import Simulation
from .experiments import batch
from .metrics import frame_metrics, series
from .model import ElectionError, make_scenario


def _write_jsonl(path: Path, data: dict) -> None:
    """Write a manifest followed by every metric and available recorded frame."""
    header = {key: data[key] for key in ("record_type", "record_version", "scenario", "manifest", "policy_digests", "recording")}
    if "stride" in data:
        header["stride"] = data["stride"]
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps({"type": "manifest", **header}, allow_nan=False) + "\n")
        for row in data["metrics"]:
            handle.write(json.dumps({"type": "metrics", "data": row}, allow_nan=False) + "\n")
        for frame in data.get("frames", []):
            handle.write(json.dumps({"type": "frame", "data": frame}, allow_nan=False) + "\n")


def _preflight_outputs(paths: list[Path | None]) -> None:
    """Reject conflicts before starting a run or creating any requested output."""
    outputs = [path for path in paths if path is not None]
    for path in outputs:
        if path.exists() or path.is_symlink():
            raise ElectionError(f"output already exists: {path}")
        if not path.parent.is_dir():
            raise ElectionError(f"output parent directory does not exist: {path.parent}")
    canonical = [path.resolve() for path in outputs]
    if len(set(canonical)) != len(outputs):
        raise ElectionError("output paths must be distinct, including aliases")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run a TOML scenario")
    run.add_argument("scenario", type=Path)
    run.add_argument("--checkpoint", type=Path, help="write final JSON checkpoint")
    recording = run.add_mutually_exclusive_group()
    recording.add_argument("--summary", action="store_true", help="stream metrics without retaining frames")
    recording.add_argument("--sample", type=int, metavar="STRIDE", help="output every STRIDE frames plus the final frame")
    run.add_argument("--jsonl", type=Path, help="write manifest, metrics and recorded frames as JSONL")
    resume = commands.add_parser("resume", help="verify and resume a JSON checkpoint")
    resume.add_argument("checkpoint", type=Path)
    resume.add_argument("--rounds", type=int, required=True, help="additional rounds")
    resume.add_argument("--output", type=Path, help="write resumed JSON checkpoint")
    resume.add_argument("--allow-environment-change", action="store_true", help="replay and migrate after reviewing runtime/core changes")
    batches = commands.add_parser("batch", help="compare scheduled edits with a matched control")
    batches.add_argument("scenario", type=Path)
    batches.add_argument("--seeds", type=int, nargs="+", required=True)
    batches.add_argument("--target", required=True)
    batches.add_argument("--csv", type=Path)
    batches.add_argument("--plot-svg", type=Path)
    batches.add_argument("--plot-png", type=Path)
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
    args = parser.parse_args(argv)
    try:
        if args.command in ("run", "batch", "visual"):
            with args.scenario.open("rb") as handle:
                scenario = make_scenario(tomllib.load(handle))
            if args.command == "batch":
                _preflight_outputs([args.csv, args.plot_svg, args.plot_png])
                if args.plot_png:
                    from .render import _pillow
                    _pillow()
                result = batch(scenario, args.seeds, args.target)
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
                server = make_server(Simulation(scenario), args.port)
                print(f"Open http://127.0.0.1:{server.server_port}/ (Ctrl-C to stop)", flush=True)
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    pass
                finally:
                    server.server_close()
                return 0
            if args.sample is not None and args.sample < 1:
                raise ElectionError("sample stride must be a positive integer")
            if args.summary and args.checkpoint:
                raise ElectionError("summary recording cannot write a full-history checkpoint")
            _preflight_outputs([args.checkpoint, args.jsonl])
            simulation = Simulation(scenario)
            if args.summary or (args.sample is not None and args.checkpoint is None):
                if args.checkpoint:
                    raise ElectionError("summary recording cannot write a full-history checkpoint")
                measured = [frame_metrics(scenario, simulation.current)]
                samples = [simulation.current.as_dict()] if args.sample is not None else []
                for _ in range(scenario.rounds):
                    previous = simulation.current
                    current = simulation.step()
                    measured.append(frame_metrics(scenario, current, previous))
                    if args.sample is not None and (current.round % args.sample == 0 or current.round == scenario.rounds):
                        samples.append(current.as_dict())
                    simulation.frames = [current]
                output_data = {"record_type": "eclipse.run", "record_version": 1,
                               "seed": scenario.seed, "parties": scenario.parties, "k": scenario.k,
                               "scenario": scenario.as_dict(), "manifest": simulation.runtime_manifest,
                               "policy_digests": {name: digest for name, (_, digest, _) in simulation.plugins.items()},
                               "recording": "summary" if args.summary else "sampled", "metrics": measured}
                if args.sample is not None:
                    output_data.update({"stride": args.sample, "frames": samples})
                if args.jsonl:
                    _write_jsonl(args.jsonl, output_data)
                print(json.dumps(output_data, indent=2))
                return 0
            simulation.run()
            output = args.checkpoint
        elif args.command == "resume":
            _preflight_outputs([args.output])
            with args.checkpoint.open(encoding="utf-8") as handle:
                simulation = Simulation.from_checkpoint(json.load(handle), allow_environment_change=args.allow_environment_change)
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
                with args.csv.open("x", encoding="utf-8", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(["round", "winner", "winner_margin", "mean_winner_rank", "ballot_switch_rate", "public_edge_count", "campaign_edge_count", "mean_out_degree", "intervention_count", "sensor_observation_count"] + [f"count:{p}" for p in simulation.scenario.parties])
                    for row in rows:
                        writer.writerow([row[k] for k in ("round", "winner", "winner_margin", "mean_winner_rank", "ballot_switch_rate", "public_edge_count", "campaign_edge_count", "mean_out_degree", "intervention_count", "sensor_observation_count")] + [row["counts"][p] for p in simulation.scenario.parties])
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
    except (OSError, json.JSONDecodeError, tomllib.TOMLDecodeError, ElectionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    result = {"record_type": "eclipse.run", "record_version": 1,
              "seed": scenario.seed, "parties": scenario.parties, "k": scenario.k,
              "scenario": scenario.as_dict(), "manifest": simulation.runtime_manifest,
              "policy_digests": {name: digest for name, (_, digest, _) in simulation.plugins.items()},
              "recording": "full", "metrics": series(scenario, simulation.frames)}
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


if __name__ == "__main__":
    raise SystemExit(main())
