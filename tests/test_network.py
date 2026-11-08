import copy
import math
import random
import unittest

from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.network import proximity_edges
from test_baseline import example


class NetworkTests(unittest.TestCase):
    def test_edges_against_independent_brute_force(self):
        positions = {"a": (0.0, 0.0), "b": (0.3, 0.4), "c": (0.3, 0.4), "d": (1.0, 1.0)}
        for radius in (0, 0.5, 1.0, math.sqrt(2)):
            expected = tuple(sorted((a, b) for a in positions for b in positions if a != b and math.dist(positions[a], positions[b]) <= radius))
            self.assertEqual(proximity_edges(positions, radius), expected)
        self.assertEqual(proximity_edges(positions, None), ())

    def test_receiver_radii_against_brute_force_and_tiny_values(self):
        rng = random.Random(8391)
        for iteration in range(80):
            positions = {str(i):(rng.randrange(5)/4, rng.randrange(5)/4) for i in range(15)}
            fallback = (None, 0, 0.25, 0.5)[iteration % 4]
            radii = {person: rng.choice((None, 0, 1e-310, 0.25, 0.5, math.sqrt(2)))
                     for person in positions if rng.random() < 0.8}
            expected = tuple(sorted((a,b) for a in positions for b in positions if a != b
                                    and radii.get(b, fallback) is not None
                                    and math.dist(positions[a],positions[b]) <= radii.get(b, fallback)))
            self.assertEqual(proximity_edges(positions, fallback, radii), expected)
        positions = {"a":(0.0,0.0),"b":(0.0,0.0),"c":(1.0,1.0)}
        self.assertEqual(proximity_edges(positions, 1e-310), (("a","b"),("b","a")))

    def test_group_radius_direction_sensing_overrides_rewind_and_replay(self):
        data = example(); data["k"] = 1
        data["groups"] = {"wide":{"voting":"sincere", "proximity_radius":0.5,
                                 "capabilities":{"sense_public_ballots":True}},
                          "narrow":{"voting":"sincere", "proximity_radius":0}}
        for index, person in enumerate(data["people"]):
            person["group"] = "wide" if index == 0 else "narrow"
            person["position"] = ([0.0,0.0], [0.3,0.4], [1.0,1.0], [1.0,0.0])[index]
        data["network"] = {"radius":0.1, "persistent_edges":[["3","4"]],
                           "campaign_edges":[["4","3"]], "private_channels":{"team":["1","2"]}}
        data["interventions"] = [{"round":1,"person":"1","group":"narrow"},
                                 {"round":2,"person":"2","overrides":{"proximity_radius":0.5}}]
        scenario = make_scenario(data); self.assertEqual(make_scenario(scenario.as_dict()),scenario)
        sim = Simulation(scenario)
        self.assertEqual(sim.current.proximity_edges, (("2","1"),))
        first = sim.step(); self.assertEqual(first.proximity_edges, ())
        self.assertEqual(first.persistent_edges, (("3","4"),))
        self.assertEqual(first.campaign_edges, (("4","3"),))
        second = sim.step(); self.assertEqual(second.proximity_edges, (("1","2"),))
        self.assertEqual(second.private_channels, (("team",("1","2")),))
        restored = Simulation.from_checkpoint(sim.checkpoint()); self.assertEqual(restored.current,sim.current)
        self.assertEqual(restored.step(),sim.step())
        sim.edit_after(0,"1",overrides={"proximity_radius":0.5,"capabilities":{"sense_public_ballots":True}})
        one = sim.step()
        self.assertEqual(one.proximity_edges, (("2","1"),))
        self.assertIn(("1","2","public",0,("A",)), one.ballot_sensors)
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current,one)

    def test_group_radius_validation_and_certified_directed_graph_guard(self):
        for value in (-1, float("nan"), True, None, math.sqrt(2)+0.01):
            data = example(); data["groups"]["residents"]["proximity_radius"] = value
            with self.subTest(value=value), self.assertRaises(ElectionError): make_scenario(data)
        import tomllib
        from pathlib import Path
        with Path("examples/certified-conformity.toml").open("rb") as handle:
            data = tomllib.load(handle)
        data["network"]["persistent_edges"] = []
        data["network"]["radius"] = 0
        data["people"][0]["position"] = [0.0,0.0]
        data["people"][1]["position"] = [0.3,0.4]
        data["people"][0]["overrides"] = {"proximity_radius":0.5}
        with self.assertRaisesRegex(ElectionError,"undirected"): make_scenario(data)
        data["people"][1]["overrides"] = {"proximity_radius":0.5}
        sim = Simulation(make_scenario(data))
        self.assertEqual(sim.current.proximity_edges, (("1","2"),("2","1")))
        self.assertEqual(Simulation.from_checkpoint(sim.checkpoint()).current, sim.current)

    def test_group_radius_example_cli_session_and_exports(self):
        import contextlib
        import csv
        import io
        import json
        import tempfile
        import tomllib
        from pathlib import Path
        from multi_agent_election.cli import main
        from multi_agent_election.visual import Session
        path = "examples/group-radius.toml"
        with Path(path).open("rb") as handle:
            scenario = make_scenario(tomllib.load(handle))
        output = io.StringIO()
        with contextlib.redirect_stdout(output): self.assertEqual(main(["run",path]),0)
        cli = json.loads(output.getvalue())
        session = Session(Simulation(scenario)); initial = session.snapshot()
        self.assertEqual(initial["proximity_radius"], 0.2)
        self.assertEqual(initial["group_proximity_radii"], {"wide":0.4,"narrow":0.1})
        self.assertEqual(initial["frames"][0]["proximity_edges"], [["2","1"]])
        for revision in range(4):
            reply = session.command({"action":"step","revision":revision})
            self.assertEqual(reply["frame"],cli["frames"][revision+1])
            self.assertEqual(reply["metric"],cli["metrics"][revision+1])
        self.assertIn(["1","2","public",0,["B"]],cli["frames"][1]["ballot_sensors"])
        self.assertNotIn(["2","1","public",0,["A"]],cli["frames"][1]["ballot_sensors"])
        self.assertEqual(cli["frames"][1]["ballots"]["1"],["B"])
        self.assertEqual(Simulation.from_checkpoint(session.simulation.checkpoint()).current,session.simulation.current)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); checkpoint = root / "checkpoint.json"
            checkpoint.write_text(json.dumps(session.simulation.checkpoint()))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["export",str(checkpoint),"--csv",str(root/"metrics.csv")]),0)
            with (root/"metrics.csv").open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([int(row["proximity_edge_count"]) for row in rows],
                             [row["proximity_edge_count"] for row in cli["metrics"]])
            self.assertEqual(rows[0]["proximity_edge_turnover"], "")
            self.assertEqual([float(row["proximity_edge_turnover"]) for row in rows[1:]],
                             [row["proximity_edge_turnover"] for row in cli["metrics"][1:]])

    def test_frozen_initial_contact_control_matches_motion_and_survives_edits(self):
        from multi_agent_election.metrics import series
        data = example(); data["k"] = 1; data["rounds"] = 3
        data["groups"] = {"wide":{"voting":"sincere", "proximity_radius":0.5,
                                 "movement":"random_walk", "max_step":0.03,
                                 "capabilities":{"sense_public_ballots":True}},
                          "narrow":{"voting":"sincere", "proximity_radius":0}}
        for index, person in enumerate(data["people"]):
            person["group"] = "wide" if index == 0 else "narrow"
            person["position"] = ([0.0,0.0], [0.3,0.4], [1.0,1.0], [1.0,0.0])[index]
        data["network"] = {"persistent_edges":[["3","4"]],"campaign_edges":[["4","3"]],
                           "private_channels":{"team":["1","2"]}}
        data["interventions"] = [{"round":1,"person":"1","position":[0.9,0.1],
                                  "overrides":{"proximity_radius":0}}]
        dynamic = Simulation(make_scenario(data))
        frozen_data = copy.deepcopy(data); frozen_data["network"]["proximity_mode"] = "frozen"
        frozen = Simulation(make_scenario(frozen_data))
        self.assertEqual(frozen.current.proximity_edges, (("2","1"),))
        dynamic.run(); frozen.run()
        self.assertEqual([f.positions for f in dynamic.frames], [f.positions for f in frozen.frames])
        self.assertTrue(all(f.proximity_edges == (("2","1"),) for f in frozen.frames))
        self.assertEqual(dynamic.frames[1].proximity_edges, ())
        self.assertEqual(frozen.frames[1].persistent_edges, (("3","4"),))
        self.assertEqual(frozen.frames[1].campaign_edges, (("4","3"),))
        self.assertEqual(frozen.frames[1].private_channels, (("team",("1","2")),))
        self.assertIn(("1","2","public",0,("A",)), frozen.frames[1].ballot_sensors)
        self.assertEqual([r["proximity_edge_turnover"] for r in series(frozen.scenario,frozen.frames)], [None,0,0,0])
        restored = Simulation.from_checkpoint(frozen.checkpoint())
        self.assertEqual(restored.step(), frozen.step())
        bad = frozen.checkpoint(); bad["frames"][1]["proximity_edges"] = []
        with self.assertRaisesRegex(ElectionError,"history"): Simulation.from_checkpoint(bad)
        frozen.edit_after(0,"2",position=[0.9,0.9])
        self.assertEqual(frozen.step().proximity_edges, (("2","1"),))
        self.assertEqual(Simulation.from_checkpoint(frozen.checkpoint()).current, frozen.current)

    def test_frozen_stationary_equivalence_and_configuration_validation(self):
        data = example(); data["network"] = {"radius":0.1}
        dynamic = make_scenario(data)
        self.assertEqual(dynamic.proximity_mode, "dynamic")
        self.assertNotIn("proximity_mode", dynamic.as_dict()["network"])
        frozen_data = copy.deepcopy(data); frozen_data["network"]["proximity_mode"] = "frozen"
        frozen = make_scenario(frozen_data)
        self.assertEqual(make_scenario(frozen.as_dict()), frozen)
        self.assertEqual(Simulation(dynamic).run(3),Simulation(frozen).run(3))
        for invalid in (None, True, "static", 0, []):
            bad = copy.deepcopy(data); bad["network"]["proximity_mode"] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(ElectionError): make_scenario(bad)

    def test_paired_network_control_reports_exposure_and_partial_failures(self):
        from unittest.mock import patch
        from multi_agent_election.experiments import compare_proximity
        data = example(); data["people"] = data["people"][:2]; data["k"] = 1; data["rounds"] = 2
        data["people"][0]["position"] = [0,0]; data["people"][1]["position"] = [0.3,0.4]
        data["network"] = {"radius":0.5}
        data["interventions"] = [{"round":1,"person":"2","position":[1,1]}]
        scenario = make_scenario(data)
        result = compare_proximity(scenario,[1,2])
        self.assertEqual(result["record_type"], "eclipse.proximity-comparison")
        for row in result["rows"]:
            self.assertEqual(row["status"],"ok"); self.assertTrue(row["movement_matched"])
            self.assertEqual(row["exposure_dynamic"],{"1":0,"2":0})
            self.assertEqual(row["exposure_frozen"],{"1":2,"2":2})
            self.assertEqual(row["exposure_delta"],{"1":-2,"2":-2})
            self.assertEqual(row["exposure_l1"],4)
        self.assertEqual(compare_proximity(scenario,[1,2]),result)
        for seeds in ([],[True],[0,0],[-1]):
            with self.subTest(seeds=seeds), self.assertRaises(ElectionError): compare_proximity(scenario,seeds)
        invalid = copy.deepcopy(data)
        invalid["interventions"].append({"round":2,"person":"1","overrides":{"movement":"python:unknown:move"}})
        with self.assertRaisesRegex(ElectionError,"built-in movement"): compare_proximity(make_scenario(invalid),[1])
        real_step = Simulation.step
        def fail_one(sim):
            if sim.scenario.proximity_mode == "frozen" and sim.current.round == 1:
                raise ElectionError("injected test failure")
            return real_step(sim)
        with patch.object(Simulation,"step",fail_one):
            failed = compare_proximity(scenario,[1])["rows"][0]
        self.assertEqual(failed["status"],"failed")
        self.assertEqual(failed["dynamic"]["status"],"ok")
        self.assertEqual(failed["frozen"]["completed_round"],1)
        self.assertNotIn("exposure_l1",failed)

    def test_static_match_is_optimal_for_calibration_and_ties_are_deterministic(self):
        import itertools
        from dataclasses import replace
        from multi_agent_election.experiments import _matched_static_edges
        data = example(); data["people"] = data["people"][:3]
        scenario = make_scenario(data); frame = Simulation(scenario).current
        rounds = [(),(("2","1"),("3","1"),("1","2")),
                  (("2","1"),("1","2")),(("3","1"),("1","3"))]
        frames = [replace(frame,round=i,proximity_edges=edges) for i,edges in enumerate(rounds)]
        selected = _matched_static_edges(frames,scenario.people)
        self.assertEqual(selected, (("1","2"),("2","1")))
        def mismatch(edges):
            return sum(abs(sum(target == receiver for period in rounds[1:] for _,target in period)
                           - 3*sum(target == receiver for _,target in edges)) for receiver in ("1","2","3"))
        all_edges = [(a,b) for a,b in itertools.permutations(("1","2","3"),2)]
        possible = [tuple(edge for i,edge in enumerate(all_edges) if mask & (1<<i)) for mask in range(64)]
        self.assertEqual(mismatch(selected),3)
        self.assertEqual(mismatch(selected),min(mismatch(edges) for edges in possible))
        with self.assertRaisesRegex(ElectionError,"at least one"): _matched_static_edges(frames[:1],scenario.people)

    def test_calibrated_static_control_is_disjoint_replayable_and_reports_residual(self):
        import tomllib
        from pathlib import Path
        from multi_agent_election.experiments import compare_proximity, _matched_static_edges
        with Path("examples/group-radius.toml").open("rb") as handle: data = tomllib.load(handle)
        scenario = make_scenario(data)
        result = compare_proximity(scenario,[11,22],[101,102])
        self.assertEqual(result["record_version"],2)
        for row, seed, calibration_seed in zip(result["rows"],(11,22),(101,102)):
            matched = row["matched_static"]
            self.assertEqual((matched["status"],matched["calibration_seed"]),("ok",calibration_seed))
            self.assertTrue(matched["movement_matched"])
            self.assertEqual(matched["scenario"]["seed"],seed)
            self.assertEqual(matched["scenario"]["network"]["proximity_mode"],"static")
            calibration_data = copy.deepcopy(data); calibration_data["seed"] = calibration_seed
            calibration = Simulation(make_scenario(calibration_data)); calibration.run()
            self.assertEqual(matched["scenario"]["network"]["static_proximity_edges"],
                             [list(edge) for edge in _matched_static_edges(calibration.frames,scenario.people)])
            replay = Simulation(make_scenario(matched["scenario"])); replay.run()
            from multi_agent_election.metrics import series
            self.assertEqual(matched["metrics"],series(replay.scenario,replay.frames))
            self.assertEqual(Simulation.from_checkpoint(replay.checkpoint()).current,replay.current)
            self.assertEqual(matched["exposure_l1"],sum(abs(x) for x in matched["exposure_delta"].values()))
            self.assertEqual(matched["calibration_exposure_l1"],sum(abs(x) for x in matched["calibration_exposure_delta"].values()))
            for person in matched["static_in_degree"]:
                self.assertEqual(matched["calibration_exposure_delta"][person],
                                 matched["calibration_exposure"][person] - scenario.rounds*matched["static_in_degree"][person])
            self.assertGreaterEqual(matched["temporal_arc_mismatch"],0)
            self.assertLessEqual(matched["temporal_arc_mismatch"],1)
        for invalid in ([11,102],[101],[101,101],[-1,102],[True,102]):
            with self.subTest(invalid=invalid), self.assertRaises(ElectionError): compare_proximity(scenario,[11,22],invalid)
        another = compare_proximity(scenario,[999],[101])["rows"][0]["matched_static"]
        self.assertEqual(another["scenario"]["network"]["static_proximity_edges"],
                         result["rows"][0]["matched_static"]["scenario"]["network"]["static_proximity_edges"])
        changed = copy.deepcopy(data); changed["interventions"] = [{"round":1,"person":"1","position":[0.3,0.3]}]
        with self.assertRaisesRegex(ElectionError,"excludes scheduled"): compare_proximity(make_scenario(changed),[11],[101])
        from unittest.mock import patch
        real_step = Simulation.step
        def calibration_failure(sim):
            if sim.scenario.seed == 101: raise ElectionError("calibration failure")
            return real_step(sim)
        with patch.object(Simulation,"step",calibration_failure):
            row = compare_proximity(scenario,[11],[101])["rows"][0]
        self.assertEqual(row["status"],"ok")
        self.assertEqual((row["matched_static"]["status"],row["matched_static"]["phase"]),("failed","calibration"))

    def test_explicit_static_graph_validation_and_certified_guard(self):
        from multi_agent_election.visual import Session
        data = example(); data["network"] = {"proximity_mode":"static", "static_proximity_edges":[["1","2"]]}
        sim = Simulation(make_scenario(data)); self.assertEqual(sim.current.proximity_edges,(("1","2"),))
        self.assertEqual(Session(sim).snapshot()["proximity_mode"], "static")
        self.assertEqual(make_scenario(sim.scenario.as_dict()),sim.scenario)
        sim.run(2); self.assertTrue(all(f.proximity_edges == (("1","2"),) for f in sim.frames))
        for mode, edges in (("dynamic",[["1","2"]]),("frozen",[]),("static",None),
                            ("static",[["1","1"]]),("static",[["1","2"],["1","2"]])):
            invalid = copy.deepcopy(data); invalid["network"] = {"proximity_mode":mode}
            if edges is not None: invalid["network"]["static_proximity_edges"] = edges
            with self.subTest(mode=mode,edges=edges), self.assertRaises(ElectionError): make_scenario(invalid)
        import tomllib
        from pathlib import Path
        with Path("examples/certified-conformity.toml").open("rb") as handle: certified = tomllib.load(handle)
        certified["network"] = {"proximity_mode":"static","static_proximity_edges":[["1","2"]]}
        with self.assertRaisesRegex(ElectionError,"undirected"): make_scenario(certified)
        certified["network"]["static_proximity_edges"].append(["2","1"])
        self.assertEqual(len(Simulation(make_scenario(certified)).current.proximity_edges),2)

    def test_network_compare_cli_output_and_frozen_summary_parity(self):
        import contextlib
        import io
        import json
        import tempfile
        from pathlib import Path
        from multi_agent_election.cli import main
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/"comparison.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["compare-networks","examples/group-radius.toml","--seeds","1","2","--output",str(output)]),0)
            self.assertEqual(json.loads(stdout.getvalue())["pairs"],2)
            result = json.loads(output.read_text())
            self.assertTrue(all(row["movement_matched"] for row in result["rows"]))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["compare-networks","examples/group-radius.toml","--seeds","1","--output",str(output)]),2)
            self.assertEqual(json.loads(output.read_text()),result)
            calibrated_output = io.StringIO()
            with contextlib.redirect_stdout(calibrated_output):
                self.assertEqual(main(["compare-networks","examples/group-radius.toml","--seeds","1","--calibration-seeds","101"]),0)
            self.assertEqual(json.loads(calibrated_output.getvalue())["rows"][0]["matched_static"]["status"],"ok")
            frozen_path = Path(folder)/"frozen.toml"
            frozen_path.write_text(Path("examples/group-radius.toml").read_text().replace("[network]\n",'[network]\nproximity_mode = "frozen"\n'))
            full, summary = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(full): self.assertEqual(main(["run",str(frozen_path)]),0)
            with contextlib.redirect_stdout(summary): self.assertEqual(main(["run",str(frozen_path),"--summary"]),0)
            full_result, summary_result = json.loads(full.getvalue()),json.loads(summary.getvalue())
            self.assertEqual(full_result["metrics"], summary_result["metrics"])
            initial_edges = full_result["frames"][0]["proximity_edges"]
            self.assertTrue(all(frame["proximity_edges"] == initial_edges for frame in full_result["frames"]))

    def test_frozen_control_http_tracks_initial_layer_and_mode(self):
        import json
        import threading
        import tomllib
        from pathlib import Path
        from urllib.request import Request, urlopen
        from multi_agent_election.visual import make_server
        with Path("examples/group-radius.toml").open("rb") as handle: data = tomllib.load(handle)
        data["network"]["proximity_mode"] = "frozen"
        data["interventions"] = [{"round":1,"person":"2","position":[0.9,0.9]}]
        expected = Simulation(make_scenario(data)); expected.step()
        server = make_server(Simulation(make_scenario(data)))
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        self.addCleanup(worker.join,2); self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_port}"
        with urlopen(base + "/") as response: html = response.read().decode()
        token = html.split('name="session-token" content="')[1].split('"')[0]
        headers = {"X-Session-Token":token,"Content-Type":"application/json"}
        with urlopen(Request(base+"/state",headers=headers)) as response: state = json.load(response)
        self.assertEqual(state["proximity_mode"],"frozen")
        body = json.dumps({"action":"step","revision":0}).encode()
        with urlopen(Request(base+"/command",data=body,headers=headers,method="POST")) as response:
            step = json.load(response)
        self.assertEqual(step["frame"],expected.current.as_dict())
        self.assertEqual(step["frame"]["proximity_edges"],state["frames"][0]["proximity_edges"])
        self.assertEqual(step["metric"]["proximity_edge_turnover"],0)

    def test_moving_agents_replay_and_persistent_edges_survive(self):
        data = example()
        data["network"] = {"radius": 0.1, "persistent_edges": [["1", "2"]]}
        data["people"][0]["position"] = [0.0, 0.0]
        data["people"][1]["position"] = [1.0, 1.0]
        data["groups"]["residents"].update(movement="random_walk", max_step=0.5)
        scenario = make_scenario(data)
        a, b = Simulation(scenario).run(6), Simulation(scenario).run(6)
        self.assertEqual(a, b)
        self.assertNotEqual(a[0].positions, a[1].positions)
        for frame in a:
            self.assertEqual(frame.persistent_edges, (("1", "2"),))
            self.assertTrue(all(0 <= coord <= 1 for _, pos in frame.positions for coord in pos))

    def test_reject_invalid_network_and_coordinates(self):
        mutations = [lambda x: x.update(network={"radius": float("nan")}),
                     lambda x: x.update(network={"radius": -1}),
                     lambda x: x.update(network={"persistent_edges": [["1", "1"]]}),
                     lambda x: x.update(network={"persistent_edges": [["1", "no"]]}),
                     lambda x: x["people"][0].update(position=[1.1, 0]),
                     lambda x: x["groups"]["residents"].update(movement="fly")]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                data = copy.deepcopy(example()); mutation(data)
                with self.assertRaises(ElectionError): make_scenario(data)

    def test_random_walk_checkpoint_continuation(self):
        data = example()
        data["groups"]["residents"].update(movement="random_walk", max_step=0.4)
        data["network"] = {"radius": 0.2}
        original = Simulation(make_scenario(data))
        original.run(3)
        resumed = Simulation.from_checkpoint(original.checkpoint())
        self.assertEqual(original.run(4), resumed.run(4))


if __name__ == "__main__": unittest.main()
