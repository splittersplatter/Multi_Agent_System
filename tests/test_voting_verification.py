"""Independent verification of response arithmetic and real HTTP integration."""

import contextlib
import csv
import io
import itertools
import json
import math
import random
import threading
import tomllib
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from multi_agent_election import Simulation, make_scenario
from multi_agent_election.cli import main
from multi_agent_election.metrics import frame_metrics
from multi_agent_election.policies import Observation
from multi_agent_election.visual import make_server
from multi_agent_election.voting import VOTING_POLICIES, _exact_gains, _pivot_weights, configure_voting, decide


class VotingVerificationTests(unittest.TestCase):
    def test_top_two_exact_tie_model_exposes_electorate_parity_limit(self):
        # This is a documented modelling limitation, not a desired convergence test.
        # N=500 -> 499 other ballots: no exact tie when only two candidates exist.
        even_population=_pivot_weights(499,(0.45,0.55),'top_k',200,200000,random.Random(1))
        odd_population=_pivot_weights(498,(0.45,0.55),'top_k',200,200000,random.Random(1))
        self.assertEqual(even_population[0][1],0.0)
        self.assertGreater(odd_population[0][1],0.0)

    def test_randomized_exact_gains_match_independent_complete_score_enumeration(self):
        rng=random.Random(74219)
        for case in range(80):
            m=rng.randint(2,5);n=rng.randint(0,10)
            raw=[rng.random()+0.01 for _ in range(m)]
            probabilities=tuple(x/sum(raw) for x in raw)
            utilities=tuple(rng.uniform(-2,3) for _ in range(m))
            expected=[0.0]*m
            # Independent stars-and-bars iterator and factorial probabilities.
            for separators in itertools.combinations(range(n+m-1),m-1):
                bounds=(-1,)+separators+(n+m-1,)
                state=tuple(bounds[i+1]-bounds[i]-1 for i in range(m))
                weight=math.factorial(n)
                for count,p in zip(state,probabilities):
                    weight=weight/math.factorial(count)*p**count
                for ballot in range(m):
                    scores=[count+(c==ballot) for c,count in enumerate(state)]
                    winner=scores.index(max(scores))
                    expected[ballot]+=weight*utilities[winner]
            actual=_exact_gains(n,probabilities,utilities,200000)
            for c in range(m):
                with self.subTest(case=case,party=c):
                    self.assertAlmostEqual(actual[c]-actual[0],expected[c]-expected[0],places=10)

    def test_pivotal_and_uncertainty_rules_against_independent_world_oracle(self):
        rng=random.Random(3911);parties=('A','B','C')
        def outcome(state,ballot):
            scores=list(state);scores[parties.index(ballot)]+=1
            return parties[scores.index(max(scores))]
        for case in range(80):
            preference=tuple(rng.sample(parties,3));current=rng.choice(parties)
            # Use a common fixed electorate per information set.
            states=[s for s in itertools.product(range(4),repeat=3) if sum(s)==4]
            states=rng.sample(states,rng.randint(1,5))
            utility={c:2-preference.index(c) for c in parties}
            obs=Observation('v',1,parties,1,preference,(0.5,0.5),(),(current,))
            values={c:[utility[outcome(s,c)] for s in states] for c in parties}
            def dominates(a,b):
                return min(x-y for x,y in zip(values[a],values[b]))>=0 and max(x-y for x,y in zip(values[a],values[b]))>0
            eligible=[c for c in preference if dominates(c,current) and not any(dominates(d,c) for d in parties)]
            wanted=eligible[0] if eligible else current
            actual,_=decide('local_dominance',obs,{'possible_scores':[list(s) for s in states]},None,rng,5,(2,2,1))
            self.assertEqual(actual[0],wanted)
            worst={c:min(values[c]) for c in parties};best=max(worst.values())
            wanted=current if worst[current]==best else next(c for c in preference if worst[c]==best)
            actual,_=decide('maximin',obs,{'possible_scores':[list(s) for s in states]},None,rng,5,(2,2,1))
            self.assertEqual(actual[0],wanted)
            others=states[0];poll=list(others);poll[parties.index(current)]+=1
            outcomes={c:utility[outcome(others,c)] for c in parties}
            best=max(outcomes.values());wanted=current
            if best>outcomes[current]:wanted=next(c for c in preference if outcomes[c]==best)
            actual,_=decide('pivotal',obs,{'poll':'explicit','initial_poll':poll},None,rng,5,poll)
            self.assertEqual(actual[0],wanted)

    def test_every_policy_real_http_equals_cli_and_exports_replayable_history(self):
        with Path('examples/heuristics.toml').open('rb') as handle:raw=tomllib.load(handle)
        for policy in VOTING_POLICIES:
            with self.subTest(policy=policy):
                scenario=configure_voting(make_scenario(raw),policy)
                expected=Simulation(scenario);expected.run(3)
                output=io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(['run','examples/heuristics.toml','--voting',policy]),0)
                cli=json.loads(output.getvalue())
                self.assertEqual(cli['frames'][:4],[f.as_dict() for f in expected.frames])
                server=make_server(Simulation(make_scenario(raw)))
                worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
                base=f'http://127.0.0.1:{server.server_port}'
                try:
                    with urlopen(base+'/') as response:html=response.read().decode()
                    token=html.split('name="session-token" content="')[1].split('"')[0]
                    headers={'X-Session-Token':token,'Content-Type':'application/json'}
                    def post(body):
                        with urlopen(Request(base+'/command',data=json.dumps(body).encode(),headers=headers)) as response:return json.load(response)
                    configured=post({'action':'configure_voting','revision':0,'policy':policy,'parameters':{}})
                    self.assertEqual(configured['frames'][0],expected.frames[0].as_dict())
                    for round_number in range(1,4):
                        actual=post({'action':'step','revision':round_number})
                        self.assertEqual(actual['frame'],expected.frames[round_number].as_dict())
                        metric=frame_metrics(scenario,expected.frames[round_number],expected.frames[round_number-1])
                        self.assertEqual(actual['metric'],json.loads(json.dumps(metric)))
                    with urlopen(Request(base+'/checkpoint?revision=4',headers=headers)) as response:checkpoint=json.load(response)
                    restored=Simulation.from_checkpoint(checkpoint)
                    self.assertEqual(restored.run(2),expected.run(2))
                    with urlopen(Request(base+'/export?format=csv&revision=4&frame=3',headers=headers)) as response:
                        rows=list(csv.DictReader(io.StringIO(response.read().decode())))
                    self.assertEqual(len(rows),4)
                finally:server.shutdown();server.server_close();worker.join(timeout=2)


if __name__=='__main__':unittest.main()
