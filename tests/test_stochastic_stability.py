"""Exact formal fixtures, never small-population outcome experiments."""

from collections import Counter
import contextlib
from dataclasses import replace
from fractions import Fraction as F
import io
from itertools import permutations, product
import json
from pathlib import Path
import tempfile
import unittest

from scripts import verify_stochastic_stability as proof
from multi_agent_election.majority import MajorityConfig, MajorityState, advance
from multi_agent_election.population import verification_scope
from multi_agent_election.voting import memory_pivotal


class StochasticContractTests(unittest.TestCase):
    def setUp(self):
        self.model = proof.Model(((0, 1), (1, 0)), (1, 1), 2, 2, 2, F(1))
        self.start = proof.initial(self.model, ((0, 0), (1, 1)))

    def test_boundary_proposals_keep_mass_instead_of_resampling(self):
        self.assertEqual(Counter(proof.move((0, 0), p, 2) for p in range(5)),
                         {(0, 0): 3, (0, 1): 1, (1, 0): 1})
        self.assertEqual(proof.move((1, 1), 1, 2), (1, 1))
        self.assertEqual(proof.move((1, 1), 3, 2), (1, 1))

    def test_kernel_matches_independent_enumeration_all_25_proposals(self):
        states = (self.start, proof.transition(self.model, self.start, (3, 0)))
        for state in states:
            expected = Counter(proof.transition(self.model, state, p) for p in product(range(5), repeat=2))
            self.assertEqual(proof.kernel(self.model, state), {s: F(n, 25) for s, n in expected.items()})
            self.assertEqual(sum(proof.kernel(self.model, state).values()), 1)

    def test_cache_expiration_reentry_and_completed_not_proposed_ballots(self):
        met = proof.transition(self.model, self.start, (3, 0))
        self.assertEqual(met.caches, (((1, 1, 0),), ((0, 0, 0),)))
        separated = proof.transition(self.model, met, (0, 4))
        self.assertEqual(separated.positions, ((1, 0), (0, 1)))
        self.assertEqual(separated.caches, (((1, 1, 1),), ((0, 0, 1),)))
        expired = proof.transition(self.model, separated, (0, 0))
        self.assertEqual(expired.caches, ((), ()))
        reentered = proof.transition(self.model, expired, (1, 0))
        self.assertEqual(reentered.caches[0], ((1, expired.ballots[1], 0),))
        self.assertEqual(expired.caches, ((), ()))  # No cross-frame mutation.

    def test_repeated_encounters_count_once_and_refresh_unchanged_votes(self):
        state = proof.transition(self.model, self.start, (3, 0))
        for _ in range(5):
            state = proof.transition(self.model, state, (0, 0))
            self.assertEqual(tuple(len(c) for c in state.caches), (1, 1))
            self.assertEqual(tuple(c[0][2] for c in state.caches), (0, 0))

    def test_startup_and_later_phase_zero_do_not_merge(self):
        model = replace(self.model, initial_poll=(9, 1))
        start = proof.initial(model, self.start.positions)
        later = replace(start, startup=False)
        self.assertEqual(proof.transition(model, start, (0, 0)).poll, (9, 1))
        self.assertEqual(proof.transition(model, later, (0, 0)).poll, (1, 1))
        for _ in range(2):
            start = proof.transition(model, start, (0, 0))
        self.assertEqual(start.phase, 0)
        self.assertEqual(start.poll, (9, 1))
        self.assertEqual(proof.transition(model, start, (0, 0)).poll, (1, 1))

    def test_default_integer_contact_boundary_including_diagonal(self):
        model = replace(self.model, side=41, window=10, interval=10, radius_squared=F(576, 25))
        for dx, dy in product(range(-40, 41), repeat=2):
            expected = (F(dx, 40)**2 + F(dy, 40)**2) <= F(3, 25)**2
            self.assertEqual(dx*dx + dy*dy <= model.radius_squared, expected)
        for point, contact in (((24, 22), True), ((24, 23), False), ((20, 20), True)):
            start = proof.initial(model, ((20, 20), point))
            self.assertEqual(bool(proof.transition(model, start, (0, 0)).caches[0]), contact)

    def test_fraction_decisions_agree_with_existing_policy_many_inputs(self):
        parties = ("A", "B", "C")
        checked = 0
        for poll in ((1, 1, 1), (2, 1, 0), (99, 1, 0)):
            config = MajorityConfig(poll, 10, .5, 0, 10)
            for phase, vote, preference, cache_choices in product(range(10), range(3), permutations(range(3)), ((), (0,), (1, 2))):
                cache = tuple((j, c, 0) for j, c in enumerate(cache_choices))
                entries = tuple((str(j), parties[c], phase + 1, phase) for j, c, _ in cache)
                state = MajorityState(phase + 1, entries, tuple(cache_choices.count(c) for c in range(3)))
                expected, _ = memory_pivotal(parties, tuple(parties[c] for c in preference), parties[vote], 3, state, config)
                actual = proof.choice(preference, vote, 3, poll, cache, F(10 - phase, 10))
                self.assertEqual(parties[actual], expected)
                checked += 1
        self.assertEqual(checked, 1620)

    def test_simultaneous_compromise_changes_read_previous_not_updated_votes(self):
        model = proof.Model(((0, 1, 2), (0, 1, 2), (1, 2, 0), (2, 1, 0)), (2, 1, 1))
        ballots = (0, 0, 1, 2)
        state = proof.State(((20, 20),) * 4, ballots, ((),) * 4, (2, 1, 1), 5, False)
        successor = proof.transition(model, state, (0,) * 4)
        self.assertEqual(successor.ballots, (0, 0, 2, 1))
        self.assertEqual(successor.caches[2], ((0, 0, 0), (1, 0, 0), (3, 2, 0)))
        self.assertEqual(successor.caches[3], ((0, 0, 0), (1, 0, 0), (2, 1, 0)))
        self.assertEqual(state.ballots, ballots)

    def test_absolute_timestamp_quotient_matches_existing_cache_and_policy(self):
        model = proof.Model(((0, 1), (0, 1), (1, 0)), (2, 1), 10, 10, 41)
        state = proof.State(((20, 20), (24, 20), (40, 40)), (0, 1, 1),
                            (((1, 0, 1), (2, 1, 0)), ((0, 0, 0),), ()), (2, 1), 0, False)
        expected = proof.transition(model, state, (0, 0, 0))
        # r=10 and r=110 have identical normalized states; test real code in absolute time.
        for r in (10, 110):
            parties = ("A", "B")
            config = MajorityConfig(model.initial_poll, 10, .5, 0, 10)
            actual_caches, actual_ballots = [], []
            for i, cache in enumerate(state.caches):
                entries = tuple((str(j), parties[c], r - age, r - age - 1) for j, c, age in cache)
                counts = tuple(sum(c == k for _, c, _ in cache) for k in range(2))
                previous = MajorityState(r, entries, counts, state.poll, r - 10)
                encounters = [(str(j), parties[state.ballots[j]], r) for j in range(3) if i != j and
                              sum((a - b)**2 for a, b in zip(state.positions[i], state.positions[j])) <= model.radius_squared]
                updated = advance(previous, observer=str(i), parties=parties, config=config, round_number=r + 1,
                                  encounters=encounters, published_counts=(1, 2))
                actual_caches.append(tuple((int(j), parties.index(c), r + 1 - seen) for j, c, seen, _ in updated.entries))
                selected, _ = memory_pivotal(parties, tuple(parties[c] for c in model.preferences[i]),
                                            parties[state.ballots[i]], 3, updated, config)
                actual_ballots.append(parties.index(selected))
            self.assertEqual(tuple(actual_caches), expected.caches)
            self.assertEqual(tuple(actual_ballots), expected.ballots)

    def test_invalid_states_and_parameters_fail_not_snap_or_fallback(self):
        for changes in ({"window": 0}, {"interval": True}, {"side": 1}, {"initial_poll": (0, 0)},
                        {"preferences": ((0, 0), (1, 0))}, {"radius_squared": .12}):
            with self.assertRaises(ValueError):
                replace(self.model, **changes)
        for changes in ({"positions": ((.1, 0), (1, 1))}, {"ballots": (0, True)},
                        {"phase": 2}, {"poll": (0, 0)}, {"poll": (1, 3)},
                        {"caches": (((0, 0, 0),), ())}, {"caches": (((1, 0, 2),), ())},
                        {"caches": (((1, 0, 0), (1, 0, 0)), ())}):
            with self.assertRaises(ValueError):
                proof.transition(self.model, replace(self.start, **changes), (0, 0))
        for proposals in ((0,), (True, 0), (5, 0), [-1, 0]):
            with self.assertRaises(ValueError):
                proof.transition(self.model, self.start, proposals)


class ExactChainTests(unittest.TestCase):
    def test_two_cycle_is_periodic_but_has_stationary_occupation(self):
        rows = [{1: F(1)}, {0: F(1)}]
        self.assertEqual(proof.recurrent_classes(rows), [(0, 1)])
        self.assertEqual(proof.period(rows, (0, 1)), 2)
        self.assertEqual(proof.stationary(rows, (0, 1)), (F(1, 2), F(1, 2)))

    def test_transient_and_two_absorbing_classes_are_not_one_limit(self):
        rows = [{1: F(1, 3), 2: F(2, 3)}, {1: F(1)}, {2: F(1)}]
        self.assertEqual(proof.recurrent_classes(rows), [(1,), (2,)])
        for component in ((1,), (2,)):
            self.assertEqual(proof.stationary(rows, component), (F(1),))
            self.assertEqual(proof.period(rows, component), 1)

    def test_nonuniform_stationary_and_iterative_large_scc(self):
        rows = [{0: F(1, 2), 1: F(1, 2)}, {0: F(1, 3), 1: F(2, 3)}]
        self.assertEqual(proof.stationary(rows, (0, 1)), (F(2, 5), F(3, 5)))
        cycle = [{(i + 1) % 2000: F(1)} for i in range(2000)]
        self.assertEqual(proof.recurrent_classes(cycle), [tuple(range(2000))])
        self.assertEqual(proof.period(cycle, tuple(range(2000))), 2000)

    def test_nonstochastic_or_partial_rows_rejected(self):
        for rows in ([{}], [{0: F(1, 2)}], [{2: F(1)}], [{0: F(-1), 1: F(2)}, {1: F(1)}]):
            with self.assertRaises(ValueError):
                proof.recurrent_classes(rows)

    def test_scope_required_and_partial_enumeration_never_calls_class_analysis(self):
        model = proof.Model(((0, 1), (1, 0)), (1, 1), 1, 1, 2, F(1))
        state = proof.initial(model, ((0, 0), (1, 1)))
        with self.assertRaises(ValueError):
            proof.enumerate_states(model, (state,))
        with verification_scope("test exact graph cutoff, not outcomes"):
            _, rows, result = proof.enumerate_states(model, (state,), max_states=1)
            self.assertEqual(rows, [])
            self.assertEqual(result["status"], "resource_cutoff")
            audit = proof.audit(model, max_states=16, max_edges=10000, stationary_ceiling=100)
            self.assertEqual(audit["classes"], "not computed from incomplete graph")

    def test_all_tiny_position_starts_have_exact_phase_uniform_stationary_classes(self):
        model = proof.Model(((0, 1), (1, 0)), (1, 1), 1, 2, 2, F(1))
        with verification_scope("exhaustive tiny position fixture"):
            result = proof.audit(model, max_states=10000, max_edges=100000, stationary_ceiling=256)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["initial_position_states"], 16)
        self.assertTrue(result["classes"])
        for component in result["classes"]:
            self.assertEqual(component["stationary_status"], "exact_residual_checked")
            self.assertEqual(component["phase_mass"], ("1/2", "1/2"))
            self.assertEqual(component["period"] % 2, 0)

    def test_stationary_solve_ceiling_is_reported_not_certified(self):
        model = proof.Model(((0, 1), (1, 0)), (1, 1), 1, 1, 2, F(1))
        with verification_scope("test independent linear-solve resource gate"):
            result = proof.audit(model, max_states=1000, max_edges=10000, stationary_ceiling=1)
        self.assertEqual(result["status"], "complete")
        self.assertTrue(all(c["stationary_status"] == "resource_cutoff" for c in result["classes"]))
        self.assertTrue(all("winner_frequency" not in c for c in result["classes"]))

    def test_cli_exclusive_outputs_and_invalid_resource_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.json"
            with contextlib.redirect_stdout(io.StringIO()):
                proof.main(["--population", "2", "--max-states", "16", "--output", str(path)])
            raw = path.read_bytes()
            record = json.loads(raw)
            self.assertEqual(len(record["cases"]), 4)
            self.assertTrue(all(r["status"] == "resource_cutoff" for r in record["cases"]))
            for args in (["--output", str(path)], ["--max-edges", "0"], ["--population", "99"]):
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    proof.main(args)
            self.assertEqual(path.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
