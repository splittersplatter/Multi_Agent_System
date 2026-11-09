"""Reproducible exploratory Gaussian study; N=200, matched seeds and controls."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from multi_agent_election.model import make_scenario
from multi_agent_election.render import export_metric_plot
import tomllib

CASES = ("mixed", "clustered", "biased-poll")
SEEDS = (2000, 2001, 2002)
RANKINGS = (("A", "B", "C"), ("B", "C", "A"), ("C", "A", "B"),
            ("A", "C", "B"), ("B", "A", "C"), ("C", "B", "A"))


def config(case):
    # Rankings/IDs match across all cases. Physical initialization uses a fixed
    # seed separate from movement seeds. Clustering changes x only.
    rng = random.Random(8192)
    lines = [f'# {case}: 200 voters; shared rankings; seed 8192 initialization.',
             'parties = ["A", "B", "C"]', 'k = 1', 'seed = 2000', 'rounds = 1000',
             '', '[majority_estimation]',
             'poll_counts = ' + ('[55, 25, 20]' if case == 'biased-poll' else '[34, 33, 33]'),
             'memory_rounds = 10', 'poll_weight = 0.5', 'poll_refresh_rounds = 10',
             '', '[network]', 'radius = 0.12', '', '[groups.people]',
             'voting = "memory_pivotal"', 'movement = "random_walk"', 'max_step = 0.05',
             'communication = "none"',
             'parameters = { movement = { distribution = "normal", mean_step = 0.025, std_step = 0.00625 } }']
    for i in range(200):
        ranking = RANKINGS[i % len(RANKINGS)]
        x, y = rng.random(), rng.random()
        if case == 'clustered':
            x = (('A', 'B', 'C').index(ranking[0]) + x) / 3
        lines += ['', '[[people]]', f'id = "p{i:03}"', 'group = "people"',
                  'preference = [' + ', '.join(json.dumps(p) for p in ranking) + ']',
                  f'position = [{x:.12f}, {y:.12f}]']
    return '\n'.join(lines) + '\n'


def execute(task):
    case, seed, control, destination, rounds = task
    stem = f'{case}-{control}-{seed}'
    command = [sys.executable, '-m', 'multi_agent_election.cli', 'frequencies',
               str(ROOT / 'examples' / 'presentation' / f'{case}.toml'), '--rounds', str(rounds),
               '--burn-in', '200', '--batch-size', '100', '--seed', str(seed),
               '--control', control, '--rows', str(destination / f'{stem}.csv'),
               '--output', str(destination / f'{stem}.json')]
    env = {**os.environ, 'PYTHONPATH': str(ROOT / 'src')}
    result = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
    (destination / f'{stem}.log').write_text(json.dumps({'command': command, 'returncode': result.returncode,
        'stdout': result.stdout, 'stderr': result.stderr}, indent=2) + '\n')
    return stem, result.returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=1000)
    parser.add_argument('--workers', type=int, default=3)
    args = parser.parse_args()
    if args.rounds < 300 or args.rounds % 100 or args.workers < 1:
        parser.error('rounds must be >=300 and divisible by 100; workers >=1')
    destination = args.output_dir.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    configs = ROOT / 'examples' / 'presentation'
    configs.mkdir(parents=True, exist_ok=True)
    for case in CASES:
        path = configs / f'{case}.toml'
        content = config(case)
        if path.exists() and path.read_text() != content:
            raise FileExistsError(f'configuration already exists and differs: {path}')
        if not path.exists():
            path.write_text(content)
        with path.open('rb') as handle:
            scenario = make_scenario(tomllib.load(handle))
        assert len(scenario.people) == 200
    tasks = [(case, seed, control, destination, args.rounds) for case in CASES
             for seed in SEEDS for control in ('baseline', 'sincere')]
    metadata = {'cases': list(CASES), 'seeds': list(SEEDS), 'rounds': args.rounds,
                'burn_in': 200, 'batch_size': 100, 'controls': ['baseline', 'sincere'],
                'population': 200, 'initialization_seed': 8192,
                'config_sha256': {case: hashlib.sha256((configs / f'{case}.toml').read_bytes()).hexdigest() for case in CASES}}
    (destination / 'protocol.json').write_text(json.dumps(metadata, indent=2) + '\n')
    errors = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for future in as_completed([pool.submit(execute, task) for task in tasks]):
            stem, code = future.result()
            print(f'{stem}: {code}', flush=True)
            if code: errors.append(stem)
    if errors:
        print(f'Failed: {errors}', file=sys.stderr)
        return 1
    # Per-round SVG source data are the actual streamed CSV, no imputed points.
    for case in CASES:
        stem = f'{case}-baseline-{SEEDS[0]}'
        with (destination / f'{stem}.csv').open(newline='') as handle:
            rows = [{'round': int(row['round']), 'shares': {p: float(row[f'share:{p}']) for p in ('A', 'B', 'C')}}
                    for row in csv.DictReader(handle)]
        export_metric_plot(('A', 'B', 'C'), rows, destination / f'{stem}-vote-shares.svg')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
