"""Motion distribution, compatibility and post-quiet contact regression checks."""

import copy
import hashlib
import math
import random
import statistics

from verification_support import VerificationTestCase
from test_baseline import example
from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.experiments import compare_heuristics
from multi_agent_election.network import random_walk


NORMAL = {"distribution": "normal", "mean_step": .025, "std_step": .00625}


class NormalWalkTests(VerificationTestCase):
    def test_uniform_legacy_draws_are_unchanged(self):
        for round_number in range(30):
            payload = f"101\0movement\0{len('person')}:person\0{round_number}".encode()
            rng = random.Random(int.from_bytes(hashlib.sha256(payload).digest(), "big"))
            angle, length = rng.random()*2*math.pi, rng.random()*.05
            expected = (.5+length*math.cos(angle), .5+length*math.sin(angle))
            self.assertEqual(random_walk((.5,.5),.05,101,"person",round_number), expected)

    def test_normal_moments_bounds_and_repeatability(self):
        lengths = []
        for index in range(5000):
            point = random_walk((.5,.5),.05,101,str(index),1,NORMAL)
            self.assertEqual(point, random_walk((.5,.5),.05,101,str(index),1,NORMAL))
            length = math.dist(point,(.5,.5)); lengths.append(length)
            self.assertTrue(0 <= length <= .05)
        self.assertAlmostEqual(statistics.mean(lengths),.025,delta=.00035)
        self.assertAlmostEqual(statistics.stdev(lengths),.00625,delta=.0003)
        # Not the legacy U(0,.05) distribution, and not a fixed-length step.
        self.assertGreater(len(set(lengths)),4900)
        for origin in ((0,0),(0,1),(1,0),(1,1)):
            for index in range(100):
                point = random_walk(origin,.05,101,str(index),2,NORMAL)
                self.assertTrue(all(0 <= coordinate <= 1 for coordinate in point))
                self.assertLessEqual(math.dist(origin,point),.05+1e-15)

    def test_symmetric_truncation_median_is_configured_mean(self):
        from unittest.mock import patch
        with patch("multi_agent_election.network.random.Random") as factory:
            factory.return_value.random.side_effect=[0,.5]
            self.assertEqual(random_walk((.5,.5),.05,101,"x",1,NORMAL),(.525,.5))

    def test_degenerate_distribution_and_invalid_parameters(self):
        self.assertEqual(random_walk((.3,.7),0,1,"x",1,{"distribution":"normal"}),(.3,.7))
        point = random_walk((.5,.5),.05,1,"x",1,dict(NORMAL,std_step=0))
        self.assertAlmostEqual(math.dist(point,(.5,.5)),.025)
        invalid = [None, [], {"distribution":"unknown"}, {"std_step":.01},
                   dict(NORMAL,mean_step=True), dict(NORMAL,mean_step=-1),
                   dict(NORMAL,mean_step=.06), dict(NORMAL,std_step=float("nan")),
                   dict(NORMAL,std_step=True), dict(NORMAL,std_step=-.01),
                   dict(NORMAL,std_step=2), dict(NORMAL,typo=1)]
        for params in invalid:
            data=example(); data["groups"]["residents"].update(
                movement="random_walk",max_step=.05,parameters={"movement":params})
            with self.subTest(params=params),self.assertRaises(ElectionError): make_scenario(data)
        with self.assertRaisesRegex(ElectionError,"representable"):
            random_walk((.5,.5),1e-310,1,"x",1,dict(NORMAL,mean_step=0,std_step=1))

    def test_normal_engine_replay_edit_overrides_and_policy_pairing(self):
        from multi_agent_election.voting import configure_voting
        data=example(); data["k"]=1
        data["groups"]["residents"].update(movement="random_walk",max_step=.05,
                                           parameters={"movement":copy.deepcopy(NORMAL)})
        for person in data["people"]: person["position"]=[.5,.5]
        original=copy.deepcopy(data)
        a=Simulation(make_scenario(data)); a.run(4)
        b=Simulation(configure_voting(make_scenario(data),"sensed_plurality")); b.run(4)
        self.assertEqual([f.positions for f in a.frames],[f.positions for f in b.frames])
        self.assertEqual(data,original)
        restored=Simulation.from_checkpoint(a.checkpoint())
        self.assertEqual(restored.step(),a.step())
        a.edit_after(1,"1",overrides={"parameters":{"movement":dict(NORMAL,std_step=0)}})
        frame=a.step()
        before=dict(a.frames[1].positions)["1"]
        self.assertAlmostEqual(math.dist(before,dict(frame.positions)["1"]),.025)
        self.assertEqual(Simulation.from_checkpoint(a.checkpoint()).current,frame)

    def test_new_contacts_restart_ballots_after_a_quiet_window(self):
        data=example(); data["k"]=1
        data["groups"]["residents"].update(voting="sensed_plurality",
            capabilities={"sense_public_ballots":True})
        for person,position in zip(data["people"],([0,0],[.2,0],[.4,0],[.6,0])):
            person["position"]=position
        data["network"]={"radius":0}
        data["interventions"]=[{"round":4,"person":"3","position":[0,0]}]
        scenario=make_scenario(data)
        early=compare_heuristics(scenario,[1],["sensed_plurality"],rounds=3,window=2)["rows"][0]
        later=compare_heuristics(scenario,[1],["sensed_plurality"],rounds=6,window=2)["rows"][0]
        self.assertTrue(early["ballot_stable_window"])
        self.assertFalse(early["stability_assessment"]["certified"])
        self.assertGreater(later["total_ballot_switches"],0)
        self.assertEqual(later["stability_assessment"]["flip_reactivations_after_quiet_window"],1)

    def test_changing_edges_with_quiet_ballots_remain_uncertified(self):
        data=example(); data["k"]=1
        data["groups"]["residents"].update(movement="random_walk",max_step=.05,
                                           parameters={"movement":NORMAL})
        for person in data["people"]: person["position"]=[.5,.5]
        data["network"]={"radius":.01}
        row=compare_heuristics(make_scenario(data),[101],["sincere"],rounds=3,window=3)["rows"][0]
        self.assertTrue(row["ballot_stable_window"])
        self.assertGreater(row["stability_assessment"]["proximity_arc_changes_in_window"],0)
        self.assertFalse(row["stability_assessment"]["certified"])
