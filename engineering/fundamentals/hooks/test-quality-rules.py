#!/usr/bin/env python3
"""Covers #328/AC-1: each PR quality condition is a numbered condition of a rule.

The rules are markdown, so the test reads each rule file and checks that every
catalog id it owns opens a numbered condition, and that the rule has the
threshold-bearing 'Where this stops' section. It stands in for nothing the
foundation gate already decides; it pins which rule owns which id.
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNERS = {
    "engineering/fundamentals/rules/test-discipline.md": ["TST-1", "TST-2", "TST-3"],
    "engineering/fundamentals/rules/contract-tests.md": ["CTR-1", "CTR-2"],
    "engineering/quality/rules/coverage-by-layer.md": ["COV-1", "COV-2", "COV-3", "COV-4", "COV-5"],
    "engineering/quality/rules/linting.md": ["LNT-1", "LNT-2", "LNT-3"],
    "engineering/security/rules/vulnerable-dependencies.md": ["SEC-1", "SEC-2", "SEC-5"],
}


class QualityRulesTest(unittest.TestCase):
    def test_each_id_is_a_numbered_condition(self):
        """#328/AC-1: every listed id opens a numbered condition of its rule."""
        for path, ids in OWNERS.items():
            text = (ROOT / path).read_text()
            for cond in ids:
                pattern = rf"^\d+\. \*\*{cond}: "
                self.assertRegex(text, re.compile(pattern, re.M), f"{path}: {cond}")

    def test_each_rule_states_where_it_stops(self):
        """#328/AC-1: every rule carries boundaries."""
        for path in OWNERS:
            text = (ROOT / path).read_text()
            self.assertIn("\n## Where this stops\n", text, path)


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
