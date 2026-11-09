"""Adversarial checks of research tooling, not production policy certification."""

from collections import Counter
import contextlib
from dataclasses import replace
from fractions import Fraction
import io
from itertools import permutations, product
import json
from pathlib import Path
import tempfile
import unittest
from verification_support import VerificationTestCase
from unittest.mock import patch

from scripts import verify_memory_voting as checker
from multi_agent_election import ElectionError, Simulation, make_scenario
from multi_agent_election.majority import MajorityConfig, MajorityState
from multi_agent_election.voting import VOTING_POLICIES
from test_baseline import example


PARTIES = ("A", "B", "C")


def compositions(total, parts):
    if parts == 1:
        yield (total,)
    else:
        for first in range(total + 1):
            for tail in compositions(total - first, parts - 1):
                yield (first, *tail)


def fraction_oracle(parties, preference, current, population, entries, config):
    """Independent arithmetic: reconstruct counts, never call shared score helper."""
    poll = tuple(Fraction(n, sum(config.poll_counts)) for n in config.poll_counts)
    weight = Fraction(float(config.poll_weight))
    if entries:
        counts = Counter(row[1] for row in entries)
        support = tuple(weight * p + (1 - weight) * Fraction(counts[c], len(entries))
                        for c, p in zip(parties, poll))
    else:
        support = poll
    outcomes = {}
    for action in parties:
        scores = {c: (population - 1) * support[i] + int(c == action) for i, c in enumerate(parties)}
        highest = max(scores.values())
        outcomes[action] = next(c for c in parties if scores[c] == highest)
    baseline = outcomes[current]
    best = next(c for c in preference if c in outcomes.values())
    return (best if preference.index(best) < preference.index(baseline) else current), baseline, tuple(outcomes.items())


class MemoryDecisionContractTests(VerificationTestCase):
    def test_exhaustive_default_decisions_against_independent_fraction_oracle(self):
        checked = 0
        for n in (2, 3, 4, 5):
            for poll in compositions(n, 3):
                config = MajorityConfig(poll)
                for size in range(n):
                    for counts in compositions(size, 3):
                        votes = tuple(c for c, count in zip(PARTIES, counts) for _ in range(count))
                        entries = tuple((f"v{i}", c, 1, 0) for i, c in enumerate(votes))
                        state = MajorityState(1, entries, counts)
                        for preference, current in product(permutations(PARTIES), PARTIES):
                            expected = fraction_oracle(PARTIES, preference, current, n, entries, config)
                            actual = checker.decision(PARTIES, preference, current, n, state, config)
                            self.assertEqual((actual.choice, actual.baseline_winner, actual.predicted_winners), expected)
                            if actual.strict_improvement:
                                self.assertLess(preference.index(actual.choice), preference.index(actual.baseline_winner))
                                self.assertEqual(dict(actual.predicted_winners)[actual.choice], actual.choice)
                            else:
                                self.assertEqual(actual.choice, current)
                            checked += 1
        self.assertEqual(checked, 20862)

    def test_counterexample_switches_to_compromise_not_majority_or_private_favorite(self):
        state = MajorityState(1, (("v1", "A", 1, 0), ("v2", "A", 1, 0), ("v4", "C", 1, 0)), (2, 0, 1))
        decision = checker.decision(PARTIES, ("B", "C", "A"), "B", 4, state, MajorityConfig((2, 1, 1)))
        self.assertEqual(decision.baseline_winner, "A")
        self.assertEqual(decision.choice, "C")
        self.assertEqual(decision.other_scores, ((7, 4), (3, 8), (7, 8)))
        self.assertEqual(dict(decision.predicted_winners), {"A": "A", "B": "A", "C": "C"})
        self.assertTrue(decision.strict_improvement)

    def test_no_beneficial_predicted_outcome_means_retain_not_unnecessary_truth_reset(self):
        state = MajorityState.initial(PARTIES)
        decision = checker.decision(PARTIES, ("B", "C", "A"), "C", 4, state,
                                    MajorityConfig((4, 0, 0), poll_weight=1))
        self.assertEqual(decision.choice, "C")
        self.assertFalse(decision.strict_improvement)

    def test_policy_has_no_time_or_position_rng_input_and_does_not_mutate_cache(self):
        config = MajorityConfig((2, 1, 1))
        state = MajorityState(1, (("v1", "A", 1, 0), ("v2", "A", 1, 0), ("v4", "C", 1, 0)), (2, 0, 1))
        actual = checker.decision(PARTIES, ("B", "C", "A"), "B", 4, state, config)
        later = replace(state, round=101, entries=tuple((p, c, seen + 100, source + 100) for p, c, seen, source in state.entries))
        self.assertEqual(checker.decision(PARTIES, ("B", "C", "A"), "B", 4, later, config), actual)
        self.assertEqual(state.entries[0], ("v1", "A", 1, 0))

    def test_population_one_empty_cache_and_weight_boundaries(self):
        empty = MajorityState.initial(PARTIES)
        for weight in (0, 0.5, 1):
            config = MajorityConfig((2, 1, 1), poll_weight=weight)
            decision = checker.decision(PARTIES, ("C", "B", "A"), "A", 1, empty, config)
            self.assertEqual(decision.choice, "C")
            self.assertEqual(decision.other_scores, ((0, 1), (0, 1), (0, 1)))

    def test_invalid_observations_fail_not_fallback(self):
        empty = MajorityState.initial(PARTIES)
        config = MajorityConfig((2, 1, 1))
        for preference, current, n, state, spec in (
                (("A", "A", "C"), "A", 4, empty, config),
                (("A", "B", "C"), "X", 4, empty, config),
                (("A", "B", "C"), "A", True, empty, config),
                (("A", "B", "C"), "A", 0, empty, config),
                (("A", "B", "C"), "A", 4, replace(empty, counts=(1, 0, 0)), config),
                (("A", "B", "C"), "A", 4, empty, replace(config, poll_weight=2))):
            with self.assertRaises(ElectionError):
                checker.decision(PARTIES, preference, current, n, state, spec)
        for state in (MajorityState(1, (("x", "A", 1, 0),), (0, 1, 0)),
                      MajorityState(1, (("x", "A", 1, 0), ("x", "A", 1, 0)), (2, 0, 0)),
                      MajorityState(11, (("x", "A", 1, 0),), (1, 0, 0)),
                      MajorityState(1, (("x", "A", 1, 1),), (1, 0, 0)),
                      MajorityState(1, (("x", "A", 2, 1),), (1, 0, 0))):
            with self.assertRaises(ElectionError):
                checker.decision(PARTIES, ("A", "B", "C"), "A", 4, state, config)


class MemoryConvergenceGateTests(VerificationTestCase):
    def test_inductive_witness_actual_movement_source_timing_and_normalized_cycle(self):
        for window in (1, 2, 10):
            for seed in (0, 101, 999):
                result = checker.witness(12, seed, window)
                self.assertEqual(result["ballot_period"], 2)
                self.assertTrue(result["genuine_movement_observed"])
                self.assertFalse(result["full_physical_state_repetition_claimed"])
                self.assertEqual(result["truthful_initial_poll"], (2, 1, 1))
                frames = result["first_rounds"]
                self.assertEqual(frames[0]["normalized_cache"], frames[2]["normalized_cache"])
                self.assertEqual(frames[1]["normalized_cache"], frames[3]["normalized_cache"])
                self.assertNotEqual(frames[0]["positions"], frames[2]["positions"])
                self.assertEqual(result["stage_c"], "exploration_allowed_convergence_uncertified")

    def test_missing_physical_contacts_cannot_be_accepted_as_witness(self):
        real = checker.proximity_edges
        with patch.object(checker, "proximity_edges", side_effect=lambda *a, **k: real(*a, **k)[1:]):
            with self.assertRaises(AssertionError):
                checker.witness(4)

    def test_complete_reduction_agrees_with_real_cache_for_all_small_truthful_profiles(self):
        for n in (2, 3):
            people = tuple(f"v{i}" for i in range(n))
            edges = tuple((s, r) for s in people for r in people if s != r)
            for preferences in product(tuple(permutations(range(3))), repeat=n):
                initial = tuple(p[0] for p in preferences)
                poll = tuple(initial.count(c) for c in range(3))
                for weight in (0, 0.5, 1):
                    for window in (1, 2, 10):
                        config = MajorityConfig(poll, window, weight)
                        states = tuple((p, MajorityState.initial(PARTIES)) for p in people)
                        current = initial
                        for tick in (1, 2, 3):
                            states = checker.advance_population(states, PARTIES, config, tick, edges,
                                                                {p: (PARTIES[b],) for p, b in zip(people, current)})
                            actual = tuple(PARTIES.index(checker.decision(PARTIES, tuple(PARTIES[c] for c in pref),
                                               PARTIES[b], n, state, config).choice)
                                           for pref, b, (_, state) in zip(preferences, current, states))
                            self.assertEqual(actual, checker.complete_transition(current, preferences, poll, weight))
                            current = actual

    def test_finite_family_is_explicit_and_contains_counterexample(self):
        audit = checker.enumerate_complete()
        self.assertEqual(audit["directly_enumerated_orbits"], 28152)
        self.assertEqual(audit["window_parameter_cases_covered"], 84456)
        self.assertEqual(len(audit["rows"]), 24)
        row = next(r for r in audit["rows"] if (r["n"], r["m"], r["weight"]) == (4, 3, "1/2"))
        self.assertGreater(row["cycles"], 0)
        for row in audit["rows"]:
            self.assertEqual(row["fixed_points"] + row["cycles"], row["profiles"])
            self.assertGreaterEqual(row["maximum_period"], 1)
        self.assertIn("not_exhausted", audit)

    def test_production_policy_requires_explicit_estimator_and_single_choice(self):
        self.assertIn("memory_pivotal", VOTING_POLICIES)
        raw = example(); raw["groups"][next(iter(raw["groups"]))]["voting"] = "memory_pivotal"
        with self.assertRaises(ElectionError):
            make_scenario(raw)
        simulation = Simulation(make_scenario(example()))
        self.assertEqual(simulation.checkpoint()["version"], 25)

    def test_evidence_output_is_exclusive_and_invalid_rounds_create_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "proof.json"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(checker.main(["--witness-only", "--output", str(output)]), 0)
            with output.open() as handle:
                evidence = json.load(handle)
            self.assertEqual(evidence["counterexample"]["status"], "verified_inductive_counterexample")
            self.assertIn("core_sha256", evidence["manifest"])
            saved = output.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                checker.main(["--output", str(output)])
            self.assertEqual(output.read_bytes(), saved)
            invalid = Path(directory) / "invalid.json"
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                checker.main(["--witness-rounds", "3", "--output", str(invalid)])
            self.assertFalse(invalid.exists())
