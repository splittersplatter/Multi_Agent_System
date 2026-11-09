"""Explicit tiny-fixture exemption; no production population check is disabled globally."""

import unittest

from multi_agent_election.population import verification_scope


class VerificationTestCase(unittest.TestCase):
    def run(self, result=None):
        with verification_scope(f"unit-test fixture: {self.id()}"):
            return super().run(result)
