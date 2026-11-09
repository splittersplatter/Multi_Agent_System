"""Validate and summarize the fixed Gaussian presentation study's raw rows."""
import csv
import json
from pathlib import Path
import sys

CASES = ('mixed', 'clustered', 'biased-poll')
PARTIES = ('A', 'B', 'C')
SEEDS = (2000, 2001, 2002)


def load(path, horizon):
    with path.open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != horizon or [int(r['round']) for r in rows] != list(range(1, horizon + 1)):
        raise ValueError(f'{path}: missing, duplicate or out-of-order rounds')
    for row in rows:
        shares = [float(row[f'share:{p}']) for p in PARTIES]
        wins = [int(row[f'winner:{p}']) for p in PARTIES]
        if abs(sum(shares) - 1) > 1e-9 or sum(wins) != 1 or not all(0 <= x <= 1 for x in shares):
            raise ValueError(f'{path}: invalid shares or winner')
    return rows


def summarize(rows):
    n = len(rows)
    winner = lambda r: next(p for p in PARTIES if int(r[f'winner:{p}']))
    return {'winner_rounds': {p: sum(winner(r) == p for r in rows) for p in PARTIES},
            'winner_final': winner(rows[-1]),
            'mean_shares': {p: sum(float(r[f'share:{p}']) for r in rows) / n for p in PARTIES},
            'ballot_switches': round(sum(float(r['ballot_flip_fraction']) * 200 for r in rows)),
            'winner_changes': sum(int(r['winner_change']) for r in rows),
            'contact_additions_per_round': sum(int(r['contact_additions']) for r in rows) / n}


def chart(root, summaries):
    colors = {'A': '#25669a', 'B': '#d98925', 'C': '#8e4b80'}
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="650" viewBox="0 0 1100 650">',
           '<rect width="1100" height="650" fill="white"/>',
           '<g font-family="Arial, sans-serif" fill="#172a37">',
           '<text x="40" y="42" font-size="25" font-weight="bold">Vote shares in the final 100 rounds</text>',
           '<text x="40" y="70" font-size="15">200 voters · memory-pivotal · 1,000 rounds · three motion seeds per scenario</text>',
           '<text x="40" y="96" font-size="13">Average submitted first-choice ballots; each bar totals 100%</text>']
    x0, width = 275, 700
    for tick in range(0, 101, 25):
        x = x0 + width * tick / 100
        out.append(f'<line x1="{x}" y1="120" x2="{x}" y2="526" stroke="#d9e0e3" stroke-width="1"/>')
        out.append(f'<text x="{x}" y="548" text-anchor="middle" font-size="13">{tick}%</text>')
    for i, case in enumerate(CASES):
        for j, seed in enumerate(SEEDS):
            y = 130 + i * 130 + j * 34
            if j == 0:
                out.append(f'<text x="40" y="{y+20}" font-size="17" font-weight="bold">{case}</text>')
            out.append(f'<text x="205" y="{y+20}" font-size="14">{seed}</text>')
            values = summaries[f'{case}-baseline-{seed}']['last_100']['mean_shares']
            x = x0
            for party in PARTIES:
                w = width * values[party]
                if w:
                    out.append(f'<rect x="{x:.2f}" y="{y}" width="{w:.2f}" height="25" fill="{colors[party]}"/>')
                if w >= 45:
                    out.append(f'<text x="{x+w/2:.2f}" y="{y+17}" text-anchor="middle" font-size="13" fill="white">{party} {values[party]*100:.1f}%</text>')
                x += w
            out.append(f'<text x="990" y="{y+19}" font-size="13">{summaries[f"{case}-baseline-{seed}"]["last_100"]["winner_final"]} wins</text>')
    out += ['<text x="40" y="588" font-size="13">Biased-poll / seed 2000 also has A at 0.5%, too narrow to label inside the bar.</text>',
            '<text x="40" y="615" font-size="13">Ties use party order A, then B, then C. Three seeds describe this setup, not population uncertainty.</text>',
            '</g></svg>']
    (root / 'last-100-vote-shares.svg').write_text('\n'.join(out) + '\n')


def main():
    root = Path(sys.argv[1]).resolve()
    protocol = json.loads((root / 'protocol.json').read_text())
    horizon, burn = protocol['rounds'], protocol['burn_in']
    summaries = {}
    for case in CASES:
        for seed in SEEDS:
            pair = {}
            for control in ('baseline', 'sincere'):
                stem = f'{case}-{control}-{seed}'
                meta = json.loads((root / f'{stem}.json').read_text())
                if meta['status'] != 'complete' or meta['completed_rounds'] != horizon:
                    raise ValueError(f'{stem}: incomplete')
                rows = load(root / f'{stem}.csv', horizon)
                pair[control] = rows
                summaries[stem] = {'all_rounds': summarize(rows), 'retained': summarize(rows[burn:]),
                                   'last_100': summarize(rows[-100:]), 'source_sha256': meta['manifest']['core_sha256']}
                for party in PARTIES:
                    expected = meta['retained']['means'][f'share:{party}']
                    actual = summaries[stem]['retained']['mean_shares'][party]
                    if abs(expected - actual) > 1e-10: raise ValueError(f'{stem}: inconsistent mean')
            for a, b in zip(pair['baseline'], pair['sincere']):
                for key in ('contact_additions', 'contact_removals'):
                    if a[key] != b[key]: raise ValueError(f'{case}/{seed}: unpaired movement {key}')
    (root / 'reviewed-summary.json').write_text(json.dumps(summaries, indent=2) + '\n')
    chart(root, summaries)
    for case in CASES:
        print(case)
        for seed in SEEDS:
            for control in ('baseline', 'sincere'):
                row = summaries[f'{case}-{control}-{seed}']
                print(seed, control, 'retained:', row['retained'], 'last100:', row['last_100'])


if __name__ == '__main__':
    main()
