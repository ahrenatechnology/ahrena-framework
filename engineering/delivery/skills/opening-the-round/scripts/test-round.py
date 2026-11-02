#!/usr/bin/env python3
"""Tests for round.py, the decidable parts of a round.

Each case runs the script as a subprocess on the fixtures beside this file and
asserts on what it printed and wrote. The fixtures are six closed Round issues
(fixtures/closed-rounds.json), a plan for the next round (fixtures/plan.json)
and a round ready to close (fixtures/round-to-close.json). The behaviours are
pinned against #225's acceptance criteria:

    #225/AC-3  the opening renders the round form's sections, refuses an
               activity without owner, done criterion or issue, and warns
               above the calibrated capacity
    #225/AC-4  the closing writes the evidence and left-over comments and the
               closing comment with its six parts and the day's numbers
    #225/AC-5  left-over activities go on top with state and round count, and
               one entering its third round is raised, not carried
    #225/AC-10 the Slack summary is 5 to 8 lines, posts only on a recorded
               standing ok, and the week's last round adds the series
    #225/AC-11 completion rate, next capacity (mean of the last 5 rounds) and
               item age come from the closed Round issues, and the opening
               uses that capacity

Usage:
    python3 engineering/delivery/skills/opening-the-round/scripts/test-round.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "round.py"
FIXTURES = HERE / "fixtures"
HISTORY = FIXTURES / "closed-rounds.json"
PLAN = FIXTURES / "plan.json"
TO_CLOSE = FIXTURES / "round-to-close.json"
# The round form ships in ahrena-contributing; read in this repository only.
FORM = HERE.parents[4] / "contributing" / "skills" / "opening-issues" / "references" / "issue-forms" / "round.yml"


def run(*args: str) -> tuple[int, str]:
    result = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def headings(text: str) -> list[str]:
    return re.findall(r"^### (.+)$", text, re.MULTILINE)


def write_json(directory: Path, name: str, payload: object) -> Path:
    path = directory / name
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def open_round(tmp: Path, plan: Path, *extra: str) -> tuple[int, str, str]:
    body = tmp / "body.md"
    code, output = run("open", str(plan), "--body", str(body), *extra)
    return code, output, body.read_text(encoding="utf-8") if body.exists() else ""


def close_round(tmp: Path, plan: Path, *extra: str) -> tuple[int, str, Path]:
    out = tmp / "closing"
    code, output = run("close", str(plan), "--history", str(HISTORY), "--out", str(out), *extra)
    return code, output, out


# --- the opening


def case_opening_sections() -> list[str]:
    """#225/AC-3: the body carries the round form's sections, in its order."""
    found: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        code, output, body = open_round(Path(tmp), PLAN)
        if code != 0:
            return [f"open exited {code}: {output.strip()}"]
        expected = ["Window", "Sessions", "Capacity", "Activities", "Out of scope"]
        if headings(body) != expected:
            found.append(f"sections are {headings(body)}, not {expected}")
        if FORM.is_file():
            labels = re.findall(r'^\s+label: "(.+)"$', FORM.read_text(encoding="utf-8"), re.MULTILINE)
            if labels != expected:
                found.append(f"the round form's labels are {labels}; the opening no longer matches the form")
        header = "| Result | Issue | Owner | Done criterion | Size | Origin | State |"
        if header not in body:
            found.append("the Activities table does not carry the seven columns")
        if "title: Round · console · 2026-10-31" not in output:
            found.append("the title was not reported")
    return found


def case_opening_refuses() -> list[str]:
    """#225/AC-3: an activity without owner, done criterion or issue is refused, each named."""
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    plan["activities"] = [
        {"result": "No owner", "issue": "#70", "owner": "", "done": "x", "size": "P"},
        {"result": "No criterion", "issue": "#71", "owner": "hermes", "size": "P"},
        {"result": "No issue", "owner": "hermes", "done": "x", "size": "M"},
    ]
    with tempfile.TemporaryDirectory() as tmp:
        code, output, body = open_round(Path(tmp), write_json(Path(tmp), "plan.json", plan))
    found = []
    if code != 1:
        found.append(f"open exited {code}, not 1, on activities missing fields")
    for expected in ("No owner: no owner", "No criterion: no done", "No issue: no issue"):
        if expected not in output:
            found.append(f"the refusal does not name '{expected}'")
    if body:
        found.append("a body was written although the plan was refused")
    return found


def case_opening_warns_above_capacity() -> list[str]:
    """#225/AC-3, #225/AC-11: the opening uses the calibrated capacity and warns above it."""
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    plan["activities"] += [
        {"result": f"Extra {n}", "issue": f"#8{n}", "owner": "hermes", "done": "x", "size": "P"} for n in range(3)
    ]
    with tempfile.TemporaryDirectory() as tmp:
        code, output, body = open_round(Path(tmp), write_json(Path(tmp), "plan.json", plan), "--history", str(HISTORY))
    found = []
    if code != 0:
        return [f"open exited {code}: {output.strip()}"]
    if "capacity: 3.8" not in output or "3.8 activities (mean of the last 5 rounds); planned 6" not in body:
        found.append("the opening did not use the capacity of 3.8 from the last five rounds")
    if "warning: the plan holds 6 activities, above the calibrated capacity of 3.8" not in output:
        found.append("no warning above the calibrated capacity")
    return found


def case_opening_carries_and_raises() -> list[str]:
    """#225/AC-5: left-overs on top with state and round count; the third round is raised."""
    with tempfile.TemporaryDirectory() as tmp:
        code, output, body = open_round(Path(tmp), PLAN, "--history", str(HISTORY))
    if code != 0:
        return [f"open exited {code}: {output.strip()}"]
    found = []
    rows = [line for line in body.splitlines() if line.startswith("| ") and "#" in line]
    if not rows or "#41" not in rows[0]:
        found.append("the carried activity #41 is not the first row")
    elif "carried, round 2" not in rows[0] or "in review" not in rows[0]:
        found.append("#41 lost its state or round count")
    if any("#42" in row for row in rows):
        found.append("#42, entering its third round, was carried instead of raised")
    if "raise: #42 would enter round 3" not in output:
        found.append("#42 was not raised to the person")
    # None dropped silently: every left-over is either carried or raised.
    last = json.loads(HISTORY.read_text(encoding="utf-8"))[-1]
    for issue in re.findall(r'"issue": "(#\d+)"', last["comments"][-1]["body"]):
        if issue not in output:
            found.append(f"{issue} was dropped silently")
    return found


def case_opening_keeps_raised() -> list[str]:
    """#225/AC-5: a raised activity the person chose to keep stays with its age."""
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    plan["activities"].append({"result": "Tunnel survives sleep", "issue": "#42", "owner": "hermes", "done": "x", "size": "G"})
    with tempfile.TemporaryDirectory() as tmp:
        code, output, body = open_round(Path(tmp), write_json(Path(tmp), "plan.json", plan), "--history", str(HISTORY))
    if code != 0:
        return [f"open exited {code}: {output.strip()}"]
    found = []
    if "raise: #42" in output:
        found.append("#42 was raised again although the plan keeps it")
    if "activity: #42 carried round 3" not in output:
        found.append("#42 did not keep its age when kept")
    return found


def case_extract_round_trips() -> list[str]:
    """The plan is recovered from the Round issue, never from a session."""
    with tempfile.TemporaryDirectory() as tmp:
        code, output, _ = open_round(Path(tmp), PLAN, "--history", str(HISTORY))
        if code != 0:
            return [f"open exited {code}: {output.strip()}"]
        code, output = run("extract", str(Path(tmp) / "body.md"))
    if code != 0:
        return [f"extract exited {code}: {output.strip()}"]
    plan = json.loads(output)
    issues = [a["issue"] for a in plan["activities"]]
    return [] if issues == ["#41", "#43", "#44"] and plan["capacity"] == 3.8 else [f"extract returned {issues}, {plan['capacity']}"]


# --- calibration


def case_calibration() -> list[str]:
    """#225/AC-11: completion rate, next capacity over the last 5 rounds, and item age."""
    found = []
    code, output = run("calibrate", "--history", str(HISTORY))
    if code != 0:
        return [f"calibrate exited {code}: {output.strip()}"]
    for expected in (
        "round 2026-10-23: 50% (2/4) outside 70-90%",
        "round 2026-10-29: 83% (5/6) healthy",
        "next capacity: 3.8 count",
        "age: #41 enters round 2",
        "age: #42 would enter round 3: raise it",
    ):
        if expected not in output:
            found.append(f"calibrate did not print '{expected}'")
    code, output = run("calibrate", "--history", str(HISTORY), "--unit", "points")
    if "next capacity: 6.4 points" not in output:
        found.append("the points capacity is not the mean of the last five rounds' points (6.4)")
    return found


# --- the closing


def case_closing() -> list[str]:
    """#225/AC-4: evidence on done issues, state/reason/next step on left-overs, a six-part closing."""
    with tempfile.TemporaryDirectory() as tmp:
        code, output, out = close_round(Path(tmp), TO_CLOSE)
        if code != 0:
            return [f"close exited {code}: {output.strip()}"]
        closing = (out / "closing.md").read_text(encoding="utf-8")
        comments = json.loads((out / "issue-comments.json").read_text(encoding="utf-8"))
    found = []
    expected = ["Delivered", "Left over", "Decisions", "Pending", "Context for tomorrow", "The day's numbers"]
    if headings(closing) != expected:
        found.append(f"closing sections are {headings(closing)}, not {expected}")
    for line in ("- Done: 2 of 4 (50%)", "- Carried to the next round: 1", "- Raised instead of carried: #45"):
        if line not in closing:
            found.append(f"the day's numbers lack '{line}'")
    pending = "- #44 needs the column order. Recommend: keep the on-screen order. https://github.com/acme/console/issues/44"
    if pending not in closing:
        found.append("the pending item is not in three parts")
    closes = {c["issue"]: c for c in comments}
    for issue in ("#41", "#43"):
        if not closes.get(issue, {}).get("close") or "Evidence:" not in closes[issue]["body"]:
            found.append(f"{issue} is not closed with an evidence comment")
    for issue in ("#44", "#45"):
        body = closes.get(issue, {}).get("body", "")
        if closes.get(issue, {}).get("close") or not all(k in body for k in ("State:", "Reason:", "Next step:")):
            found.append(f"{issue} lacks state, reason and next step, or is closed")
    if "raised to the person" not in closes.get("#45", {}).get("body", ""):
        found.append("#45, at its second round, is not marked as raised")
    if "<!-- round-data:" not in closing:
        found.append("the closing carries no round-data block for the next opening")
    return found


def case_closing_refuses() -> list[str]:
    """#225/AC-4: a done activity without evidence, or a left-over without a reason, is refused."""
    plan = json.loads(TO_CLOSE.read_text(encoding="utf-8"))
    plan["activities"][0]["evidence"] = ""
    plan["activities"][2]["reason"] = ""
    plan["pending"][0]["recommend"] = ""
    with tempfile.TemporaryDirectory() as tmp:
        code, output, out = close_round(Path(tmp), write_json(Path(tmp), "round.json", plan))
        wrote = out.exists()
    found = []
    if code != 1:
        found.append(f"close exited {code}, not 1")
    for expected in ("#41: done with no evidence", "#44: left over with no reason", "no recommend"):
        if expected not in output:
            found.append(f"the refusal does not name '{expected}'")
    if wrote:
        found.append("the closing was written although it was refused")
    return found


def case_slack_and_week() -> list[str]:
    """#225/AC-10: 5 to 8 lines, posted only on a standing ok, and the week's series on its last round."""
    found = []
    with tempfile.TemporaryDirectory() as tmp:
        code, output, out = close_round(Path(tmp), TO_CLOSE, "--channel", "#console")
        if code != 0:
            return [f"close exited {code}: {output.strip()}"]
        lines = (out / "slack.txt").read_text(encoding="utf-8").splitlines()
        if not 5 <= len(lines) <= 8:
            found.append(f"the Slack summary has {len(lines)} lines")
        if "no standing ok for #console: ask the person before posting" not in output:
            found.append("without a standing ok the closing did not say to ask")
        if (out / "week.txt").exists():
            found.append("the week's series was written on a round that is not the week's last")
        instructions = Path(tmp) / "AGENTS.md"
        instructions.write_text("# Project\n\nahrena:round-slack-ok #console\n", encoding="utf-8")
        code, output, out = close_round(Path(tmp), TO_CLOSE, "--channel", "#console", "--instructions", str(instructions), "--week-last")
        if "standing ok recorded for #console" not in output:
            found.append("a recorded standing ok was not read")
        code, other, _ = close_round(Path(tmp), TO_CLOSE, "--channel", "#elsewhere", "--instructions", str(instructions))
        if "ask the person" not in other:
            found.append("a standing ok for one channel was applied to another")
        week = (out / "week.txt").read_text(encoding="utf-8") if (out / "week.txt").exists() else ""
    rows = [line for line in week.splitlines() if re.match(r"\d{4}-\d{2}-\d{2}: ", line)]
    if len(rows) != 6 or "Week 44" not in week:
        found.append(f"the week's series has {len(rows)} rows, not the six rounds of week 44")
    if "Oldest items: #45 (round 2)" not in week:
        found.append("the week's series does not name the oldest item")
    return found


def case_language() -> list[str]:
    """Screen labels follow the person's language; keys and identifiers do not."""
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    plan["language"] = "pt-BR"
    to_close = json.loads(TO_CLOSE.read_text(encoding="utf-8"))
    to_close["language"] = "pt-BR"
    found = []
    with tempfile.TemporaryDirectory() as tmp:
        code, output, body = open_round(Path(tmp), write_json(Path(tmp), "plan.json", plan))
        if headings(body) != ["Janela", "Sessões", "Capacidade", "Atividades", "Fora do escopo"]:
            found.append(f"pt-BR opening headings are {headings(body)}")
        if "title: Rodada · console · 31/10/2026" not in output:
            found.append("the pt-BR title is not dated dd/mm/aaaa")
        code, output, out = close_round(Path(tmp), write_json(Path(tmp), "round.json", to_close))
        closing = (out / "closing.md").read_text(encoding="utf-8")
        if "Recomendo: keep the on-screen order." not in closing or "### Números do dia" not in closing:
            found.append("the pt-BR closing does not use the pt-BR labels")
        if '"points_done"' not in closing:
            found.append("the data block keys are not English")
        plan["language"] = "fr"
        code, output, _ = open_round(Path(tmp), write_json(Path(tmp), "plan.json", plan))
        if code != 1 or "no labels for language 'fr'" not in output:
            found.append("an unknown language was not refused")
    return found


CASES = [
    ("the opening renders the round form's sections (#225/AC-3)", case_opening_sections),
    ("the opening refuses an activity without owner, done criterion or issue (#225/AC-3)", case_opening_refuses),
    ("the opening uses the calibrated capacity and warns above it (#225/AC-3, #225/AC-11)", case_opening_warns_above_capacity),
    ("left-overs go on top with state and round count; the third round is raised (#225/AC-5)", case_opening_carries_and_raises),
    ("a raised activity the person keeps stays with its age (#225/AC-5)", case_opening_keeps_raised),
    ("the plan is recovered from the Round issue body", case_extract_round_trips),
    ("completion rate, next capacity and item age come from the closed rounds (#225/AC-11)", case_calibration),
    ("the closing writes evidence, left-over comments and the six-part closing (#225/AC-4)", case_closing),
    ("the closing refuses missing evidence, reason or recommendation (#225/AC-4)", case_closing_refuses),
    ("the Slack summary, its standing ok and the week's series (#225/AC-10)", case_slack_and_week),
    ("labels follow the person's language", case_language),
]


def main() -> int:
    failed = 0
    for name, case in CASES:
        problems = case()
        if not problems:
            print(f"ok    {name}")
            continue
        failed += 1
        print(f"FAIL  {name}")
        for problem in problems:
            print(f"        {problem}")
    print()
    if failed:
        print(f"{failed} of {len(CASES)} cases failed.")
        return 1
    print(f"{len(CASES)} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
