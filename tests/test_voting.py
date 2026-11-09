import contextlib
import copy
import io
import itertools
import json
import math
import random
import threading
import unittest
from verification_support import VerificationTestCase
from dataclasses import replace

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.cli import main
from multi_agent_election.experiments import compare_heuristics
from multi_agent_election.policies import Observation
from multi_agent_election.visual import Session
from multi_agent_election.visual import make_server
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch
from multi_agent_election.voting import (STRATEGIC, _exact_scores, _exact_gains, _pivot_states, _pivot_weights,
    _poisson_weights, _sample_multinomial, configure_voting, decide, uncertainty_states, validate_parameters)
from test_baseline import example


def observation(preference=("A", "B", "C"), current="A", neighbors=("B", "B", "C")):
    return Observation("self", 1, ("A", "B", "C"), 2, preference, (0.5, 0.5), (),
                       (current, next(c for c in preference if c != current)), (), (),
                       tuple((str(i), "public", 0, (c,)) for i, c in enumerate(neighbors)))


def response(policy, obs=None, params=None, total=5, memory=None, seed=12):
    return decide(policy, obs or observation(), params or {}, memory, random.Random(seed), total, (1, 2, total-3))


class VotingTests(VerificationTestCase):
    def test_pivotal_requires_improved_winner_not_popularity(self):
        params = {"poll": "explicit", "initial_poll": [1, 2, 3]}
        ballot, trace = response("pivotal", params=params, total=6)
        self.assertEqual(ballot, ("B", "A"))  # A->B prevents C winning.
        ballot, _ = response("pivotal", params={"poll": "explicit", "initial_poll": [1, 4, 0]})
        self.assertEqual(ballot[0], "A")  # Not pivotal: cannot change B's win.
        self.assertTrue(trace["switched"])

    def test_poll_memory_only_tracks_observed_changes_and_own_ballot(self):
        _, state = response("pivotal", params={"poll":"explicit", "initial_poll":[1,2,2]})
        obs = observation(current="B", neighbors=("B", "C", "C"))
        _, updated = response("pivotal", obs, {"poll":"explicit", "initial_poll":[1,2,2]}, memory=state)
        self.assertEqual(updated["scores"], [0, 2, 3])
        # A newly visible identity is not falsely counted as an observed deviation.
        added = replace(obs, sensed_ballots=obs.sensed_ballots + (("new", "public", 1, ("A",)),))
        _, again = response("pivotal", added, {"poll":"explicit", "initial_poll":[1,2,2]}, memory=updated)
        self.assertEqual(again["scores"], updated["scores"])

    def test_expected_utility_matches_independent_labelled_ballot_enumeration(self):
        probs, utilities = (0.2, 0.5, 0.3), (1.0, 0.4, 0.0)
        actual = _exact_scores(4, probs, utilities, 1000)
        oracle = [0.0] * 3
        for votes in itertools.product(range(3), repeat=4):
            weight = math.prod(probs[c] for c in votes)
            for choice in range(3):
                all_votes = votes + (choice,)
                win = max(range(3), key=lambda c: (all_votes.count(c), -c))
                oracle[choice] += weight * utilities[win]
        for a, b in zip(actual, oracle): self.assertAlmostEqual(a, b, places=12)
        gains=_exact_gains(4,probs,utilities,1000)
        for c in range(3):self.assertAlmostEqual(gains[c]-gains[0],oracle[c]-oracle[0],places=12)

    def test_exact_pivotal_optimization_includes_multiway_ties_and_near_ties(self):
        for m in (1,2,3,4):
            for n in range(7):
                probs=tuple((i+1)/(m*(m+1)/2) for i in range(m))
                utilities=tuple(float(m-i) for i in range(m))
                full=_exact_scores(n,probs,utilities,10000)
                gains=_exact_gains(n,probs,utilities,10000)
                for c in range(m):self.assertAlmostEqual(gains[c]-gains[0],full[c]-full[0],places=11)

    def test_pivot_enumerator_exhaustive_small_counts_including_two_candidates(self):
        for size in (2, 3, 4):
            for total in range(8):
                for x, y in itertools.combinations(range(size), 2):
                    oracle = {s for s in itertools.product(range(total+1), repeat=size)
                              if sum(s) == total and s[x] == s[y] and all(s[c] < s[x] for c in range(size) if c not in (x,y))}
                    self.assertEqual(set(_pivot_states(total,size,x,y)), oracle)

    def test_uniform_pivot_sampling_with_full_coverage_equals_exact(self):
        probs = (0.4, 0.35, 0.25)
        exact = _pivot_weights(8, probs, "top_k", 1000, 1000, random.Random(3))
        sampled = _pivot_weights(8, probs, "tie_u", 1000, 1000, random.Random(3))
        self.assertEqual(exact, sampled)

    def test_two_candidate_pivots_are_not_silently_empty(self):
        for policy in ("top_k", "max_m", "tie_u", "tie_h", "poisson"):
            matrix = _pivot_weights(4, (0.3,0.7), policy, 20, 1000, random.Random(1))
            self.assertGreater(matrix[0][1], 0, policy)

    def test_tie_r_matches_monte_carlo_frequency_not_uniform_state_weights(self):
        matrix = _pivot_weights(2, (0.5,0.5), "tie_r", 20000, 10000, random.Random(9))
        self.assertAlmostEqual(matrix[0][1], 0.5, delta=0.02)

    def test_multinomial_sampler_preserves_counts_means_and_degenerate_cases(self):
        rng=random.Random(99);totals=[0,0,0]
        for _ in range(10000):
            sample=_sample_multinomial(20,(0.1,0.3,0.6),rng)
            self.assertEqual(sum(sample),20)
            for c,n in enumerate(sample):self.assertGreaterEqual(n,0);totals[c]+=n
        for actual,want in zip(totals,(20000,60000,120000)):
            self.assertAlmostEqual(actual/10000,want/10000,delta=0.08)
        self.assertEqual(_sample_multinomial(10,(0,1,0),rng),[0,10,0])
        self.assertEqual(_sample_multinomial(10,(1,0,0),rng),[10,0,0])
        self.assertEqual(_sample_multinomial(0,(1,0,0),rng),[0,0,0])

    def test_poisson_weights_match_independent_small_probability_sum(self):
        probs = (0.5,0.3,0.2); n = 5
        matrix = _poisson_weights(n, probs, 10000)
        def pmf(c,k): return math.exp(-n*probs[c])*(n*probs[c])**k/math.factorial(k)
        oracle = {}
        for x,y in itertools.combinations(range(3),2):
            z = next(c for c in range(3) if c not in (x,y))
            oracle[x,y] = sum(pmf(x,k)*pmf(y,k)*sum(pmf(z,j) for j in range(k)) for k in range(35))
        scale = max(oracle.values())
        for (x,y), value in oracle.items(): self.assertAlmostEqual(matrix[x][y], value/scale, places=10)

    def test_uncertainty_set_matches_independent_grid_and_conserves_population(self):
        center = (2,1,1)
        expected = {s for s in itertools.product(range(5),repeat=3) if sum(s)==4 and sum(abs(a-b) for a,b in zip(s,center))<=2}
        self.assertEqual(set(uncertainty_states(center,2,100)), expected)
        with self.assertRaises(ElectionError): uncertainty_states(center, 4, 1)

    def test_local_dominance_and_maximin_use_worlds_not_mean_outcomes(self):
        # Others=(0,2,3): A wins nothing; voting B makes a B/C tie won by B.
        params = {"possible_scores":[[0,2,3]]}
        for policy in ("local_dominance","maximin"):
            ballot, trace = response(policy, params=params, total=6)
            self.assertEqual(ballot[0], "B", policy)
            self.assertEqual(trace["state_count"],1)
        # A is best in one world and a switch harms it: no robust domination.
        ballot,_ = response("local_dominance", params={"possible_scores":[[0,2,3],[2,2,1]]}, total=6)
        self.assertEqual(ballot[0], "A")
        ballot,_=response("maximin",params={"possible_scores":[[0,2,3],[2,2,1]]},total=6)
        self.assertEqual(ballot[0],"B")  # Worst-case B=.5 exceeds A=0 despite A's upside.

    def test_top_k_restricts_consideration_and_max_m_is_not_summed_gain(self):
        ballot,trace=response("top_k",params={"top_k":1})
        self.assertEqual(ballot[0],"B");self.assertEqual(trace["considered"],["B"])
        weights=[[0,1,0.5],[1,0,1.4],[0.5,1.4,0]]
        # Independent arithmetic: sum(A)=1 > sum(B)=.2, but max(B)=.7 > max(A)=.5.
        with patch("multi_agent_election.voting._pivot_weights",return_value=weights):
            a,_=response("top_k",observation(current="C"),{"top_k":3})
            b,_=response("max_m",observation(current="C"))
        self.assertEqual(a[0],"A");self.assertEqual(b[0],"B")

    def test_no_observation_leak_and_duplicate_sensor_is_not_an_extra_vote(self):
        obs = observation()
        duplicate = replace(obs, sensed_ballots=obs.sensed_ballots + (("0","team",0,("B",)),),
                            messages=(("secret","public",("A",)),))
        for policy in STRATEGIC:
            self.assertEqual(response(policy,obs),response(policy,duplicate), policy)

    def test_invalid_inputs_and_resource_limits_fail_not_fallback(self):
        invalid = [{"samples":True},{"top_k":0},{"max_states":0},{"uncertainty_radius":-1},
                   {"oops":1},{"poll":"explicit"},{"utility_mode":"explicit"},
                   {"possible_scores":[]},{"initial_poll":[1,2,2]},
                   {"utility_mode":"explicit","utilities":{"A":float("nan")}}]
        for params in invalid:
            with self.subTest(params=params), self.assertRaises(ElectionError): validate_parameters(params,("A","B","C"),5)
        with self.assertRaises(ElectionError): response("expected_utility",params={"max_states":1})
        with self.assertRaises(ElectionError): response("maximin",params={"possible_scores":[[1,1,1]]})
        with self.assertRaises(ElectionError): response("expected_utility",params={"utility_mode":"explicit","utilities":{"A":0,"B":1,"C":0}})

    def test_all_policies_valid_ballots_resume_and_rewind(self):
        raw=example(); raw["network"]={"radius":1}
        raw["groups"]["residents"]["capabilities"]={"sense_public_ballots":True}
        for policy in STRATEGIC:
            with self.subTest(policy=policy):
                scenario=configure_voting(make_scenario(raw),policy,{"samples":20})
                sim=Simulation(scenario); sim.run(3)
                for frame in sim.frames:
                    for _,ballot in frame.ballots:
                        self.assertEqual(len(ballot),scenario.k);self.assertEqual(len(set(ballot)),scenario.k)
                restored=Simulation.from_checkpoint(sim.checkpoint())
                self.assertEqual(sim.run(2),restored.run(2))
                sim.edit_after(1, "1", position=[0.1,0.1]); sim.run(2)
                self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).frames,sim.frames)

    def test_atomic_failure_keeps_all_frames_and_old_memory(self):
        scenario=configure_voting(make_scenario(example()),"expected_utility",{"max_states":1})
        sim=Simulation(scenario); before=sim.checkpoint()
        with self.assertRaisesRegex(ElectionError,"max_states"): sim.step()
        self.assertEqual(sim.checkpoint(),before)

    def test_startup_selection_preserves_permissions_and_locks_after_first_step(self):
        session=Session(Simulation(make_scenario(example())))
        before=session.simulation.scenario
        result=session.command({"action":"configure_voting","revision":0,"policy":"top_k","parameters":{}})
        self.assertEqual(result["revision"],1)
        self.assertFalse(result["startup_voting_locked"])
        self.assertEqual(before.groups[0].capabilities,session.simulation.scenario.groups[0].capabilities)
        with self.assertRaisesRegex(ElectionError,"stale"):session.command({"action":"step","revision":0})
        session.command({"action":"step","revision":1})
        with self.assertRaisesRegex(ElectionError,"before"):session.command({"action":"configure_voting","revision":2,"policy":"sincere","parameters":{}})
        other=Session(Simulation(make_scenario(example())))
        edited=other.command({"action":"edit","revision":0,"round":0,"person":"1","changes":{"position":[0.1,0.1]}})
        self.assertTrue(edited["startup_voting_locked"])

    def test_cli_selects_policy_and_rejects_malformed_json(self):
        out,err=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            self.assertEqual(main(["run","examples/baseline.toml","--voting","maximin"]),0)
        data=json.loads(out.getvalue())
        self.assertEqual(data["scenario"]["groups"]["residents"]["voting"],"maximin")
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(err):
            self.assertEqual(main(["run","examples/baseline.toml","--voting","pivotal","--voting-parameters","["]),2)

    def test_comparison_records_failures_and_does_not_call_window_convergence(self):
        report=compare_heuristics(make_scenario(example()),[3,4],["sincere","expected_utility"],{"max_states":1},rounds=3,window=2)
        self.assertEqual(len(report["rows"]),4)
        for row in report["rows"]:
            if row["policy"]=="expected_utility":
                self.assertEqual(row["status"],"failed");self.assertIn("max_states",row["error"])
            else:
                self.assertEqual(row["status"],"observed_ballot_stability")
                self.assertEqual(row["total_ballot_switches"],0)
        with self.assertRaises(ElectionError):compare_heuristics(make_scenario(example()),[1,1],["sincere"])

    def test_matched_policies_share_every_movement_draw_and_respect_hidden_boundary(self):
        raw=example();raw["network"]={"radius":0}
        raw["groups"]["residents"].update(movement="random_walk",max_step=0.03,capabilities={"sense_public_ballots":False})
        sims=[Simulation(configure_voting(make_scenario(raw),p)) for p in ("sincere","expected_utility","tie_h")]
        for sim in sims:sim.run(3)
        self.assertEqual([f.positions for f in sims[0].frames],[f.positions for f in sims[1].frames])
        self.assertEqual([f.positions for f in sims[0].frames],[f.positions for f in sims[2].frames])
        changed=copy.deepcopy(raw);changed["people"][1]["preference"]=["C","B","A"]
        a=Simulation(configure_voting(make_scenario(raw),"expected_utility"));b=Simulation(configure_voting(make_scenario(changed),"expected_utility"))
        self.assertEqual(dict(a.step().ballots)["1"],dict(b.step().ballots)["1"])
        self.assertEqual(dict(a.current.policy_memory)["1"],dict(b.current.policy_memory)["1"])

    def test_explicit_utility_and_all_ballot_lengths_singleton_electorate(self):
        raw={"parties":["A","B","C"],"k":1,"groups":{"g":{"voting":"sincere"}},
             "people":[{"id":"one","group":"g","preference":["C","B","A"]}]}
        for policy in STRATEGIC:
            for k in (1,2,3):
                raw["k"]=k
                sim=Simulation(configure_voting(make_scenario(raw),policy))
                self.assertEqual(len(dict(sim.step().ballots)["one"]),k)
        ballot,_=response("maximin",params={"utility_mode":"explicit","utilities":{"A":10,"B":3,"C":-5},"possible_scores":[[0,2,3]]},total=6)
        self.assertEqual(ballot[0],"B")

    def test_http_startup_selection_checkpoint_and_failed_config_are_atomic(self):
        server=make_server(Simulation(make_scenario(example())))
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        base=f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base+"/") as r:html=r.read().decode()
            token=html.split('name="session-token" content="')[1].split('"')[0]
            headers={"X-Session-Token":token,"Content-Type":"application/json"}
            def post(body):
                with urlopen(Request(base+"/command",data=json.dumps(body).encode(),headers=headers)) as r:return json.load(r)
            with self.assertRaises(HTTPError) as error:
                post({"action":"configure_voting","revision":0,"policy":"maximin","parameters":{"possible_scores":[]}})
            self.assertEqual(error.exception.code,400);error.exception.close()
            result=post({"action":"configure_voting","revision":0,"policy":"maximin","parameters":{}})
            self.assertEqual(result["startup_voting"]["residents"]["policy"],"maximin")
            post({"action":"step","revision":1})
            with urlopen(Request(base+"/checkpoint?revision=2",headers=headers)) as r:checkpoint=json.load(r)
            restored=Simulation.from_checkpoint(checkpoint)
            self.assertEqual(restored.scenario.groups[0].voting,"maximin")
            self.assertEqual(restored.current.round,1)
        finally:server.shutdown();server.server_close();worker.join(timeout=2)


if __name__ == "__main__": unittest.main()
