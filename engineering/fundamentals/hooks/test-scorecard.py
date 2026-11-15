#!/usr/bin/env python3
"""Tests for scorecard.py.

Covers #325/AC-1 to AC-4. A case builds a scratch repository with a base and a
head commit, runs the runner as a subprocess and asserts on its exit code and
on the JSON it wrote. The ratchet cases use a registry written for the case and
a stand-in detector that reports a failure for every line holding a marker, so
each pins one behaviour of `scope` without depending on a TypeScript detector.
The last cases read the registry the plugin ships.

Usage:
    python3 engineering/fundamentals/hooks/test-scorecard.py
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import json  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
from pathlib import Path  # noqa: E402

RUNNER = Path(__file__).resolve().parent / "scorecard.py"

MARKER_DETECTOR = '''
import sys
from pathlib import Path
found = []
for path in sorted(Path(".").rglob("*.txt")):
    for number, text in enumerate(path.read_text().splitlines(), 1):
        if "MARK" in text:
            found.append(f"{path}:{number}\\n    [demo] condition 1: marker")
if found:
    print(f"{len(found)} failure(s) across 1 file(s):\\n")
    print("\\n".join(found))
    sys.exit(1)
print("0 failure(s)")
'''

CRASHING_DETECTOR = "import sys\nprint('boom', file=sys.stderr)\nsys.exit(3)\n"
FLAGS_ALWAYS = "import sys\nprint('x.txt\\n    [demo] condition 1: always')\nsys.exit(1)\n"
FLAGS_NEVER = "print('0 file(s), no failures.')\n"
FLAGS_OTHER = "import sys\nprint('x.txt\\n    [demo] condition 9: other')\nsys.exit(1)\n"


def sh(cwd: Path, *args: str) -> str:
    done = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def commit(repo: Path, files: dict[str, str], message: str) -> str:
    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text, encoding="utf-8")
    sh(repo, "git", "add", "-A")
    sh(repo, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message)
    return sh(repo, "git", "rev-parse", "HEAD")


def new_repo(tmp: Path) -> Path:
    repo = tmp / "repo"
    repo.mkdir()
    sh(repo, "git", "init", "-q", "-b", "main")
    return repo


def registry(tmp: Path, detector: str, **options: str | int) -> Path:
    script = tmp / "detector.py"
    script.write_text(detector, encoding="utf-8")
    for side, body in (("clean", "nothing\n"), ("planted", "MARK\n")):
        (tmp / "fx" / side).mkdir(parents=True, exist_ok=True)
        (tmp / "fx" / side / "a.txt").write_text(body, encoding="utf-8")
    spec = {
        "id": "demo-1",
        "condition": "DEM-1",
        "rule": "demo",
        "number": 1,
        "kind": options.get("kind", "eliminatory"),
        "scope": options.get("scope", "added"),
        "threshold": options.get("threshold", 0),
        "threshold_source": "policy:test",
        "fixtures": {"clean": str(tmp / "fx" / "clean"), "planted": str(tmp / "fx" / "planted")},
    }
    path = tmp / "registry.json"
    path.write_text(json.dumps({"schema": 1, "detectors": [{"id": "demo", "path": str(script), "languages": ["any"], "conditions": [spec]}]}))
    return path


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-B", str(RUNNER), *args], cwd=cwd, capture_output=True, text=True)


def card_for(repo: Path, base: str, head: str, extra: list[str]) -> tuple[int, dict, str]:
    out = repo.parent / "card.json"
    done = run(["--base", base, "--head", head, "--out", str(out), *extra], repo)
    return done.returncode, (json.loads(out.read_text()) if out.exists() else {}), done.stderr


def check_ac1_scorecard_json() -> list[str]:
    """#325/AC-1: a base and a head write the scorecard JSON."""
    with tempfile.TemporaryDirectory() as raw:
        repo = new_repo(Path(raw))
        base = commit(repo, {"src/a.ts": "export const a = (): number => 1;\n", "src/a.test.ts": "export {};\n"}, "base")
        head = commit(repo, {"src/f.ts": "export const f = (): number => 1;\n"}, "head")
        code, card, _ = card_for(repo, base, head, [])
    cond = card.get("conditions", {}).get("TST-1", {})
    wrong = []
    if code != 1:
        wrong.append(f"expected exit 1 for a failed eliminatory condition, got {code}")
    if card.get("head") != head or card.get("base") != base:
        wrong.append("the card does not name the base and the head")
    if (cond.get("status"), cond.get("kind")) != ("failed", "eliminatory"):
        wrong.append(f"TST-1 should be failed and eliminatory: {cond}")
    if not any(f["file"] == "src/f.ts" for f in cond.get("failures", [])):
        wrong.append("TST-1 should name src/f.ts as a failure")
    if card.get("summary", {}).get("eliminatory_failed") != ["TST-1"]:
        wrong.append(f"summary should list TST-1: {card.get('summary')}")
    return wrong


def check_ac3_added_lines_only() -> list[str]:
    """#325/AC-3: a line threshold counts only the lines the change adds."""
    wrong = []
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        repo = new_repo(tmp)
        base = commit(repo, {"a.txt": "MARK old\nMARK older\nfine\n"}, "base")
        untouched = commit(repo, {"b.txt": "fine\n"}, "unrelated")
        added = commit(repo, {"b.txt": "fine\nMARK new\n"}, "adds one")
        reg = ["--registry", str(registry(tmp, MARKER_DETECTOR))]
        code, card, _ = card_for(repo, base, untouched, reg)
        if code != 0 or card["conditions"]["DEM-1"]["entries"][0]["count"] != 0:
            wrong.append("legacy failures on lines the change did not add must not count")
        code, card, _ = card_for(repo, base, added, reg)
        lines = [(f["file"], f["line"]) for f in card["conditions"]["DEM-1"]["failures"]]
        if code != 1 or lines != [("b.txt", 2)]:
            wrong.append(f"only the added line should fail, got exit {code} and {lines}")
        lenient = ["--registry", str(registry(tmp, MARKER_DETECTOR, threshold=1))]
        if card_for(repo, base, added, lenient)[0] != 0:
            wrong.append("one added failure should pass a threshold of one")
    return wrong


def check_ac3_total_ratchet() -> list[str]:
    """#325/AC-3: a total indicator fails only when it drops against the base."""
    wrong = []
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        repo = new_repo(tmp)
        base = commit(repo, {"a.txt": "MARK 1\nMARK 2\n"}, "base")
        same = commit(repo, {"a.txt": "MARK 2\nMARK 1\n"}, "reorder")
        better = commit(repo, {"a.txt": "MARK 1\n"}, "fix one")
        worse = commit(repo, {"a.txt": "MARK 1\nMARK 2\nMARK 3\n"}, "add one")
        reg = ["--registry", str(registry(tmp, MARKER_DETECTOR, kind="indicator", scope="total"))]
        for name, head, status in (("same", same, "passed"), ("better", better, "passed"), ("worse", worse, "failed")):
            code, card, _ = card_for(repo, base, head, reg)
            got = card["conditions"]["DEM-1"]["status"]
            if got != status:
                wrong.append(f"{name}: expected {status}, got {got}")
            if code != 0:
                wrong.append(f"{name}: an indicator never blocks, got exit {code}")
    return wrong


def check_ac2_fixtures_prove_detectors() -> list[str]:
    """#325/AC-2: a detector that flags its clean fixture or passes its planted one fails."""
    wrong = []
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        for name, detector, expected in (
            ("a sound detector", MARKER_DETECTOR, 0),
            ("a detector that flags everything", FLAGS_ALWAYS, 1),
            ("a detector that passes everything", FLAGS_NEVER, 1),
        ):
            done = run(["--fixtures", "--registry", str(registry(tmp, detector))], tmp)
            if done.returncode != expected:
                wrong.append(f"{name}: expected exit {expected}, got {done.returncode}: {done.stdout}")
        if "flags its clean fixture" not in run(["--fixtures", "--registry", str(registry(tmp, FLAGS_ALWAYS))], tmp).stdout:
            wrong.append("the failure should say the detector flagged its clean fixture")
        if "passes its planted fixture" not in run(["--fixtures", "--registry", str(registry(tmp, FLAGS_NEVER))], tmp).stdout:
            wrong.append("the failure should say the detector passed its planted fixture")
    return wrong


def check_a_detector_that_cannot_answer_is_an_error() -> list[str]:
    """A crash, or a condition the registry does not name, exits 2 and never passes."""
    wrong = []
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        repo = new_repo(tmp)
        base = commit(repo, {"a.txt": "x\n"}, "base")
        head = commit(repo, {"a.txt": "y\n"}, "head")
        for name, detector in (("crashes", CRASHING_DETECTOR), ("reports an unregistered condition", FLAGS_OTHER)):
            code, _, err = card_for(repo, base, head, ["--registry", str(registry(tmp, detector))])
            if code != 2 or not err.strip():
                wrong.append(f"a detector that {name} should exit 2 with a reason, got {code}")
    return wrong


def check_planted_fixtures_in_the_repository_do_not_fail_it() -> list[str]:
    """A planted defect inside a registered fixture tree is the proof, not a failure of the change."""
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        repo = new_repo(tmp)
        base = commit(repo, {"a.txt": "fine\n"}, "base")
        head = commit(repo, {"fx/clean/a.txt": "fine\n", "fx/planted/a.txt": "MARK\n"}, "adds fixtures")
        path = registry(tmp, MARKER_DETECTOR)
        spec = json.loads(path.read_text())
        fixtures = spec["detectors"][0]["conditions"][0]["fixtures"]
        fixtures["clean"], fixtures["planted"] = str(repo / "fx" / "clean"), str(repo / "fx" / "planted")
        path.write_text(json.dumps(spec))
        code, card, _ = card_for(repo, base, head, ["--registry", str(path)])
    return [] if code == 0 and card["conditions"]["DEM-1"]["status"] == "passed" else [f"expected a pass, got exit {code}"]


def check_ac4_typescript_detectors_registered() -> list[str]:
    """#325/AC-4: the five TypeScript detectors are on the scorecard."""
    with tempfile.TemporaryDirectory() as raw:
        repo = new_repo(Path(raw))
        base = commit(repo, {"src/a.ts": "export const a = (): number => 1;\n", "src/a.test.ts": "export {};\n"}, "base")
        head = commit(repo, {"README.md": "docs\n"}, "head")
        code, card, err = card_for(repo, base, head, [])
    wanted = {"STR-1", "STR-2", "STR-3", "TST-1", "TYP-2", "TYP-4", "TYP-5", "TYP-6", "TYP-7", "ERR-5", "SEC-4"}
    got = set(card.get("conditions", {}))
    wrong = [f"missing from the scorecard: {sorted(wanted - got)}"] if wanted - got else []
    if code != 0:
        wrong.append(f"a clean change should pass every condition, got exit {code}: {err}")
    return wrong


def check_ac2_shipped_fixtures_pass() -> list[str]:
    """#325/AC-2: every detector the plugin registers passes its own pair."""
    done = run(["--fixtures"], RUNNER.parent)
    return [] if done.returncode == 0 else [done.stdout + done.stderr]


CASES = [
    check_ac1_scorecard_json,
    check_ac2_fixtures_prove_detectors,
    check_ac2_shipped_fixtures_pass,
    check_ac3_added_lines_only,
    check_ac3_total_ratchet,
    check_a_detector_that_cannot_answer_is_an_error,
    check_planted_fixtures_in_the_repository_do_not_fail_it,
    check_ac4_typescript_detectors_registered,
]


def main() -> int:
    failed = 0
    for check in CASES:
        problems = check()
        failed += bool(problems)
        print(f"{'FAIL' if problems else 'ok  '}  {check.__name__}")
        for problem in problems:
            print(f"        {problem}")
    print(f"\n{failed} of {len(CASES)} cases failed." if failed else f"\n{len(CASES)} cases passed.")
    return int(bool(failed))


if __name__ == "__main__":
    sys.exit(main())
