import copy
import contextlib
import csv
import io
import itertools
import json
from pathlib import Path
import tomllib
import tempfile
import unittest
from verification_support import VerificationTestCase

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.cli import main
from multi_agent_election.epistemic import KnowledgeModel, SIGNAL_EPISTEMIC_POLICIES, response_from_observation
from multi_agent_election.policies import Observation
from multi_agent_election.visual import Session


def observation(*, report=(1, 1, 0), bound_round=1, k=1, ballot=("A",), sensed=()):
    return Observation("0", bound_round, ("A", "B", "C"), k, ("C", "B", "A"), (0., 0.), (), ballot,
                       sensed_ballots=sensed, electorate=("0", "1"),
                       public_signal=(0, 1, report))


def explicit_model(obs, bound):
    parties = obs.parties
    known = {sender: ballot for sender, _, _, ballot in obs.sensed_ballots}
    worlds = []
    for other_pref in itertools.permutations(parties):
        for other_ballot in itertools.permutations(parties, obs.k):
            if "1" in known and known["1"] != other_ballot:
                continue
            counts = [int(obs.own_previous_ballot[0] == p) + int(other_ballot[0] == p) for p in parties]
            if obs.public_signal[0] == obs.round - 1 and sum(abs(a-b) for a, b in zip(counts, obs.public_signal[2])) > 2 * bound:
                continue
            number = str(len(worlds))
            worlds.append({"id": number, "preferences": {"0": list(obs.own_preference), "1": list(other_pref)},
                           "ballots": {"0": list(obs.own_previous_ballot), "1": list(other_ballot)},
                           "observations": {"0": "same", "1": number},
                           "public_signal": list(obs.public_signal[2])})
    if not worlds:
        return None
    return KnowledgeModel.from_dict({"parties": list(parties), "k": obs.k, "agents": ["0", "1"],
                                     "actual": "0", "worlds": worlds}, max_worlds=10000)


def example():
    with Path("examples/public-signal.toml").open("rb") as handle:
        data = tomllib.load(handle)
    data["groups"]["signal_voter"].update(voting="epistemic_signal_dominant",
        capabilities={"observe_public_signal": True, "observe_electorate": True},
        parameters={"voting": {"signal_distortion_bound": 1, "remember_observations": True}})
    return data


class SignalEpistemicTests(VerificationTestCase):
    def test_all_small_reports_against_explicit_knowledge_worlds(self):
        for k in (1, 2):
            for ballot in itertools.permutations(("A", "B", "C"), k):
                for report in ((a, b, 2-a-b) for a in range(3) for b in range(3-a)):
                    for bound in (0, 1):
                        for sensed in ((), (("1", "public", 0, tuple(("B", "C")[:k])),)):
                            obs = observation(report=report, k=k, ballot=ballot, sensed=sensed)
                            model = explicit_model(obs, bound)
                            for policy in SIGNAL_EPISTEMIC_POLICIES:
                                params = {"signal_distortion_bound": bound}
                                if model is None:
                                    with self.assertRaisesRegex(ElectionError, "empty epistemic information set"):
                                        response_from_observation(policy, obs, params)
                                    continue
                                selected, trace = response_from_observation(policy, obs, params)
                                exact = model.analyze("0")
                                for field in ("world_count", "de_dicto", "de_re", "dominant", "pessimistic"):
                                    self.assertEqual(trace[field], exact[field], (k, ballot, report, bound, sensed, policy, field))
                                candidates = exact[{"epistemic_signal_dere": "de_re",
                                                    "epistemic_signal_dominant": "dominant",
                                                    "epistemic_signal_pessimistic": "pessimistic"}[policy]]
                                if policy.endswith("pessimistic") and candidates:
                                    worst = {c: max(obs.own_preference.index(w) for w in exact["action_winners"][c])
                                             for c in candidates}
                                    candidates = [c for c in candidates if worst[c] == min(worst.values())]
                                self.assertEqual(selected[0], candidates[0] if candidates else ballot[0])

    def test_stale_report_does_not_constrain_current_worlds(self):
        obs = observation(report=(0, 0, 2), bound_round=2)
        for suffix in ("dere", "dominant", "pessimistic"):
            ballot, trace = response_from_observation("epistemic_signal_" + suffix, obs, {"signal_distortion_bound": 0})
            ordinary, prior = response_from_observation("epistemic_" + suffix, obs, {})
            self.assertEqual(ballot, ordinary)
            for field in ("world_count", "projected_ballot_profiles", "de_dicto", "de_re", "dominant", "pessimistic"):
                self.assertEqual(trace[field], prior[field])
            self.assertEqual(trace["signal"]["use"], "stale_unconstrained")

    def test_three_voters_exact_world_multiplicities_and_scores(self):
        from dataclasses import replace
        obs = replace(observation(report=(1, 1, 1), k=2, ballot=("A", "B")), electorate=("0", "1", "2"))
        perms = tuple(itertools.permutations(obs.parties))
        ballots = tuple(itertools.permutations(obs.parties, obs.k))
        for bound in (0, 1):
            worlds = []
            projected = set()
            for p1, p2, b1, b2 in itertools.product(perms, perms, ballots, ballots):
                counts = [int(obs.own_previous_ballot[0] == c) + int(b1[0] == c) + int(b2[0] == c) for c in obs.parties]
                if sum(abs(a-b) for a, b in zip(counts, obs.public_signal[2])) > 2 * bound:
                    continue
                projected.add((b1[0], b2[0]))
                wid = str(len(worlds))
                worlds.append({"id": wid, "preferences": {"0": list(obs.own_preference), "1": list(p1), "2": list(p2)},
                               "ballots": {"0": list(obs.own_previous_ballot), "1": list(b1), "2": list(b2)},
                               "observations": {"0": "same", "1": wid, "2": wid},
                               "public_signal": list(obs.public_signal[2])})
            model = KnowledgeModel.from_dict({"parties": list(obs.parties), "k": obs.k, "agents": ["0", "1", "2"],
                                              "actual": "0", "worlds": worlds}, max_worlds=10000)
            for policy in SIGNAL_EPISTEMIC_POLICIES:
                _, trace = response_from_observation(policy, obs, {"signal_distortion_bound": bound})
                exact = model.analyze("0")
                self.assertEqual(trace["world_count"], len(worlds))
                self.assertEqual(trace["projected_ballot_profiles"], len(projected))
                for field in ("de_dicto", "de_re", "dominant", "pessimistic"):
                    self.assertEqual(trace[field], exact[field])

    def test_malformed_or_conflicting_reports_and_caps_fail_closed(self):
        obs = observation()
        for signal in (None, (-1, 0, (1, 1, 0)), (0, 2, (1, 1, 0)),
                       (0, 1, (True, 1, 0)), (0, 1, (-1, 2, 1)), (0, 1, (1, 0, 0))):
            from dataclasses import replace
            with self.subTest(signal=signal), self.assertRaises(ElectionError):
                response_from_observation("epistemic_signal_dere", replace(obs, public_signal=signal), {"signal_distortion_bound": 1})
        with self.assertRaisesRegex(ElectionError, "max_worlds"):
            response_from_observation("epistemic_signal_dere", obs, {"signal_distortion_bound": 1, "max_worlds": 5})
        for value in (None, True, -1, 1.5):
            with self.assertRaises(ElectionError):
                response_from_observation("epistemic_signal_dere", obs, {"signal_distortion_bound": value})
        with self.assertRaises(ElectionError):
            response_from_observation("epistemic_dere", obs, {"signal_distortion_bound": 1})

    def test_configuration_soundness_and_atomic_permission_revocation(self):
        data = example()
        for mutate in (lambda x: x["groups"]["signal_voter"]["parameters"]["voting"].update(signal_distortion_bound=0),
                       lambda x: x["groups"]["signal_voter"]["capabilities"].update(observe_electorate=False),
                       lambda x: x["groups"]["signal_voter"]["capabilities"].update(observe_public_signal=False),
                       lambda x: x.pop("signal_controller")):
            invalid = copy.deepcopy(data); mutate(invalid)
            with self.subTest(invalid=invalid), self.assertRaises(ElectionError): make_scenario(invalid)
        truthful = copy.deepcopy(data); truthful["signal_controller"]["policy"] = "truthful"
        truthful["groups"]["signal_voter"]["parameters"]["voting"]["signal_distortion_bound"] = 0
        Simulation(make_scenario(truthful)).step()
        sim = Simulation(make_scenario(data)); sim.step()
        sim.edit_after(1, "4", overrides={"capabilities": {"observe_public_signal": False}})
        before = sim.checkpoint()
        with self.assertRaisesRegex(ElectionError, "public-signal and electorate permissions"): sim.step()
        self.assertEqual(sim.checkpoint(), before)

    def test_hidden_truth_cannot_affect_identical_signal_and_observations(self):
        left = example(); right = copy.deepcopy(left)
        right["people"][1]["preference"] = ["C", "A", "B"]
        a, b = Simulation(make_scenario(left)), Simulation(make_scenario(right))
        a.step(); b.step()
        self.assertNotEqual(a.current.signal_latest[3], b.current.signal_latest[3])
        self.assertEqual(a.current.signal_latest[2], b.current.signal_latest[2])
        self.assertEqual(dict(a.current.policy_memory)["4"], dict(b.current.policy_memory)["4"])
        self.assertEqual(dict(a.current.ballots)["4"], dict(b.current.ballots)["4"])

    def test_engine_history_cli_session_checkpoint_replay_and_legacy(self):
        data = example(); sim = Simulation(make_scenario(data)); session = Session(sim)
        for revision in range(3): session.command({"revision": revision, "action": "step"})
        first = sim.frames[1].as_dict()["policy_memory"]["4"]
        self.assertEqual(first["signal"]["report"], [1, 2, 1])
        self.assertEqual(first["signal"]["use"], "current_count_constraint")
        self.assertNotIn("source_truth", json.dumps(first))
        self.assertEqual(len(sim.current.as_dict()["policy_memory"]["4"]["observation_history"]), 3)
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)
        old = sim.checkpoint(); old["version"] = 16
        with self.assertRaisesRegex(ElectionError, "version 17"): Simulation.from_checkpoint(old)
        legacy = Simulation(make_scenario({**data, "groups": {**data["groups"], "signal_voter": {
            "voting": "signal_confident", "capabilities": {"observe_public_signal": True}}}}))
        legacy.run(2); checkpoint = legacy.checkpoint(); checkpoint["version"] = 16
        self.assertEqual(Simulation.from_checkpoint(checkpoint).current, legacy.current)
        sim.edit_after(1, "3", ballot=["C"]); sim.run(2)
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)
        data["signal_controller"]["schedule"] = "initial"
        stale = Simulation(make_scenario(data)); stale.run(2)
        self.assertEqual(stale.current.as_dict()["policy_memory"]["4"]["signal"]["use"], "stale_unconstrained")

    def test_example_cli_csv_and_http_match_engine(self):
        path = "examples/epistemic-public-signal.toml"
        with Path(path).open("rb") as handle:
            scenario = make_scenario(tomllib.load(handle))
        direct = Simulation(scenario); direct.run()
        output = io.StringIO()
        with contextlib.redirect_stdout(output): self.assertEqual(main(["run", path]), 0)
        self.assertEqual(json.loads(output.getvalue())["frames"], [f.as_dict() for f in direct.frames])
        with tempfile.TemporaryDirectory() as folder:
            checkpoint = Path(folder) / "checkpoint.json"; csv_path = Path(folder) / "metrics.csv"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["run", path, "--checkpoint", str(checkpoint)]), 0)
                self.assertEqual(main(["export", str(checkpoint), "--csv", str(csv_path)]), 0)
            with csv_path.open(newline="") as handle: rows = list(csv.DictReader(handle))
            self.assertEqual(rows[1]["signal_report:B"], "2")
        import threading
        from urllib.request import Request, urlopen
        from multi_agent_election.visual import make_server
        server = make_server(Simulation(scenario)); worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        self.addCleanup(worker.join, 2); self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_port}"
        with urlopen(base + "/") as response: html = response.read().decode()
        token = html.split('name="session-token" content="')[1].split('"')[0]
        headers = {"X-Session-Token": token, "Content-Type": "application/json"}
        request = Request(base + "/command", headers=headers,
                          data=json.dumps({"action": "step", "revision": 0}).encode(), method="POST")
        with urlopen(request) as response: reply = json.load(response)
        self.assertEqual(reply["frame"], direct.frames[1].as_dict())
        self.assertEqual(reply["frame"]["policy_memory"]["4"]["signal"]["use"], "current_count_constraint")


if __name__ == "__main__":
    unittest.main()
