#!/usr/bin/env python3
"""The decidable parts of a round: its opening body, its closing, its calibration.

The round method is in engineering/delivery/docs/round-method.md. Everything a
person decides (which activities, whether to post, what to drop) stays with the
person; this script does what a rule can: refuse an activity without an owner, a
done criterion or an issue; compute capacity, completion rate and item age from
the project's closed Round issues; carry left-over activities with their state
and round count; raise one instead of carrying it into its third round; and
render the Round issue body, the closing comment, the per-activity comments, the
Slack summary and the week's series.

Every rendered text a person reads takes its labels from LABELS, so the round is
written in the person's language. Keys and identifiers stay English.

Each closing carries its numbers in a hidden `round-data` block, and each
opening carries its plan in a hidden `round-plan` block. The next opening and
the calibration read those blocks back, so a round is recovered from its issue
and never from a session.

Usage:
    python3 round.py open PLAN.json [--history ROUNDS.json] [--body OUT.md]
    python3 round.py extract BODY.md
    python3 round.py close ROUND.json [--history ROUNDS.json] [--out DIR]
                     [--week-last] [--channel NAME] [--instructions FILE]
    python3 round.py calibrate --history ROUNDS.json [--unit count|points]

ROUNDS.json is the output of
    gh issue list --label round --state closed --json number,title,url,comments

Exit status: 0 done, 1 refused (the report says why), 2 a usage error.
Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SIZES = {"P": 1, "M": 2, "G": 3}
CALIBRATION_WINDOW = 5
RAISE_AT = 3
HEALTHY = (0.70, 0.90)
STANDING_OK = "ahrena:round-slack-ok"
PLAN_MARK = "round-plan"
DATA_MARK = "round-data"

LABELS = {
    "en": {
        "title": "Round",
        "window": "Window",
        "sessions": "Sessions",
        "capacity": "Capacity",
        "activities": "Activities",
        "out_of_scope": "Out of scope",
        "columns": ["Result", "Issue", "Owner", "Done criterion", "Size", "Origin", "State"],
        "new": "new",
        "carried": "carried, round {n}",
        "planned": "planned",
        "lean": "lean mode: PM only",
        "nothing": "none",
        "uncalibrated": "no closed rounds yet, so no calibrated capacity",
        "capacity_line": "{cap} {unit} (mean of the last {k} rounds); planned {planned}",
        "units": {"count": "activities", "points": "points"},
        "delivered": "Delivered",
        "left_over": "Left over",
        "decisions": "Decisions",
        "pending": "Pending",
        "context": "Context for tomorrow",
        "numbers": "The day's numbers",
        "recommend": "Recommend:",
        "evidence": "Evidence",
        "state": "State",
        "reason": "Reason",
        "next_step": "Next step",
        "done_of_planned": "Done: {done} of {planned} ({rate})",
        "points_line": "Points: {done} of {planned}",
        "carried_line": "Carried to the next round: {n}",
        "next_capacity": "Next capacity: {cap}",
        "raised_line": "Raised instead of carried: {items}",
        "closed_by": "Done in round {round}.",
        "left_by": "Left over in round {round}; moves to the next round.",
        "left_raised": "Left over in round {round}, its round {n}; raised to the person to split, reassign or drop.",
        "slack_head": "*Round · {project} · {date}* — {done}/{planned} ({rate})",
        "slack_delivered": "Delivered: {items}",
        "slack_left": "Left over: {items}",
        "slack_pending": "Pending for you: {n}{first}",
        "slack_capacity": "Next capacity: {cap}",
        "slack_link": "Round issue: {link}",
        "week_head": "*Week {week} · {project}*",
        "week_row": "{date}: {rate} ({done}/{planned}), capacity {cap}",
        "week_oldest": "Oldest items: {items}",
        "round_n": "round {n}",
    },
    "pt-BR": {
        "title": "Rodada",
        "window": "Janela",
        "sessions": "Sessões",
        "capacity": "Capacidade",
        "activities": "Atividades",
        "out_of_scope": "Fora do escopo",
        "columns": ["Resultado", "Issue", "Dono", "Critério de pronto", "Tamanho", "Origem", "Estado"],
        "new": "nova",
        "carried": "carregada, rodada {n}",
        "planned": "planejada",
        "lean": "modo enxuto: só o PM",
        "nothing": "nada",
        "uncalibrated": "nenhuma rodada fechada ainda, então sem capacidade calibrada",
        "capacity_line": "{cap} {unit} (média das últimas {k} rodadas); planejado {planned}",
        "units": {"count": "atividades", "points": "pontos"},
        "delivered": "Entregue",
        "left_over": "Ficou para a próxima",
        "decisions": "Decisões",
        "pending": "Pendências",
        "context": "Contexto para amanhã",
        "numbers": "Números do dia",
        "recommend": "Recomendo:",
        "evidence": "Evidência",
        "state": "Estado",
        "reason": "Motivo",
        "next_step": "Próximo passo",
        "done_of_planned": "Feito: {done} de {planned} ({rate})",
        "points_line": "Pontos: {done} de {planned}",
        "carried_line": "Carregadas para a próxima rodada: {n}",
        "next_capacity": "Próxima capacidade: {cap}",
        "raised_line": "Levadas a você em vez de carregadas: {items}",
        "closed_by": "Feita na rodada {round}.",
        "left_by": "Ficou da rodada {round}; vai para a próxima rodada.",
        "left_raised": "Ficou da rodada {round}, a sua rodada {n}; levada a você para dividir, reatribuir ou largar.",
        "slack_head": "*Rodada · {project} · {date}* — {done}/{planned} ({rate})",
        "slack_delivered": "Entregue: {items}",
        "slack_left": "Ficou para a próxima: {items}",
        "slack_pending": "Pendências com você: {n}{first}",
        "slack_capacity": "Próxima capacidade: {cap}",
        "slack_link": "Issue da rodada: {link}",
        "week_head": "*Semana {week} · {project}*",
        "week_row": "{date}: {rate} ({done}/{planned}), capacidade {cap}",
        "week_oldest": "Itens mais antigos: {items}",
        "round_n": "rodada {n}",
    },
}


class Refused(Exception):
    """The input breaks a condition of the round method; the message says which."""


# --- small helpers


def labels(language: str) -> dict:
    if language not in LABELS:
        raise Refused(f"no labels for language '{language}'; known: {', '.join(LABELS)}")
    return LABELS[language]


def show_date(iso: str, language: str) -> str:
    day = date.fromisoformat(iso)
    return day.strftime("%d/%m/%Y") if language == "pt-BR" else day.isoformat()


def show_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}"


def show_rate(done: int, planned: int) -> str:
    return f"{round(100 * done / planned)}%" if planned else "-"


def hidden(mark: str, payload: dict) -> str:
    return f"<!-- {mark}: {json.dumps(payload, ensure_ascii=False, sort_keys=True)} -->"


def read_hidden(mark: str, text: str) -> dict | None:
    found = re.search(rf"<!-- {mark}: (\{{.*?\}}) -->", text, re.DOTALL)
    return json.loads(found.group(1)) if found else None


def weight(activity: dict, unit: str) -> int:
    return SIZES[activity["size"]] if unit == "points" else 1


# --- validation


def check_activity(activity: dict) -> list[str]:
    """The fields an activity cannot go without, by condition 4 of round-roles."""
    name = activity.get("result") or activity.get("issue") or "an activity"
    problems = [f"{name}: no {field}" for field in ("owner", "done", "issue") if not str(activity.get(field, "")).strip()]
    if activity.get("size") not in SIZES:
        problems.append(f"{name}: size is {activity.get('size')!r}, not one of P, M, G")
    return problems


def check_plan(plan: dict) -> None:
    problems = [p for a in plan.get("activities", []) for p in check_activity(a)]
    if problems:
        raise Refused("activities refused, open their issue or fill them first:\n  " + "\n  ".join(problems))


# --- history and calibration


def closed_rounds(history: list[dict]) -> list[dict]:
    """Each closed Round issue's data block, oldest first."""
    rounds = []
    for issue in history:
        for comment in reversed(issue.get("comments", [])):
            data = read_hidden(DATA_MARK, comment.get("body", ""))
            if data:
                rounds.append({**data, "url": issue.get("url", ""), "number": issue.get("number")})
                break
    return sorted(rounds, key=lambda r: r["date"])


def capacity(rounds: list[dict], unit: str) -> float | None:
    """Mean done over the last rounds; None with no history."""
    recent = rounds[-CALIBRATION_WINDOW:]
    if not recent:
        return None
    key = "points_done" if unit == "points" else "done"
    return round(sum(r[key] for r in recent) / len(recent), 1)


def completion(round_data: dict) -> float | None:
    return round_data["done"] / round_data["planned"] if round_data["planned"] else None


def carry_over(rounds: list[dict]) -> tuple[list[dict], list[dict]]:
    """The last round's left-over activities: carried on top, or raised at their third round."""
    if not rounds:
        return [], []
    carried, raised = [], []
    for item in rounds[-1].get("left_over", []):
        rounds_in = item.get("rounds", 1) + 1
        moved = {**item, "rounds": rounds_in, "origin": "carried"}
        (raised if rounds_in >= RAISE_AT else carried).append(moved)
    return carried, raised


# --- opening


def opening(plan: dict, history: list[dict]) -> dict:
    words = labels(plan.get("language", "en"))
    unit = plan.get("unit", "count")
    rounds = closed_rounds(history)
    carried, raised = carry_over(rounds)
    # A raised activity the plan names again is one the person chose to keep:
    # it stays with its age, and is no longer waiting on them.
    named = {a.get("issue") for a in plan.get("activities", [])}
    kept = [a for a in raised if a["issue"] in named]
    raised = [a for a in raised if a["issue"] not in named]
    carried_issues = {a["issue"] for a in carried + kept}
    fresh = [
        {**a, "origin": "new", "rounds": 1, "state": words["planned"]}
        for a in plan.get("activities", [])
        if a.get("issue") not in carried_issues
    ]
    activities = carried + kept + fresh
    check_plan({"activities": activities})
    cap = capacity(rounds, unit)
    planned = sum(weight(a, unit) for a in activities)
    warnings = []
    if cap is not None and planned > cap:
        warnings.append(f"the plan holds {planned} {LABELS['en']['units'][unit]}, above the calibrated capacity of {show_number(cap)}")
    final = {**plan, "activities": activities, "capacity": cap, "unit": unit}
    return {"plan": final, "raised": raised, "warnings": warnings, "body": render_body(final, planned)}


def origin_text(activity: dict, words: dict) -> str:
    return words["carried"].format(n=activity["rounds"]) if activity["origin"] == "carried" else words["new"]


def render_body(plan: dict, planned: int) -> str:
    words = labels(plan.get("language", "en"))
    unit = plan["unit"]
    cap = plan["capacity"]
    if cap is None:
        cap_text = words["uncalibrated"]
    else:
        cap_text = words["capacity_line"].format(
            cap=show_number(cap), unit=words["units"][unit], k=CALIBRATION_WINDOW, planned=planned
        )
    rows = ["| " + " | ".join(words["columns"]) + " |", "|" + "---|" * len(words["columns"])]
    for a in plan["activities"]:
        cells = [a["result"], a["issue"], a["owner"], a["done"], a["size"], origin_text(a, words), a.get("state", "")]
        rows.append("| " + " | ".join(str(c).replace("|", "\\|") for c in cells) + " |")
    sessions = plan.get("sessions") or [words["lean"]]
    scope = plan.get("out_of_scope") or [words["nothing"]]
    parts = [
        (words["window"], plan["window"]),
        (words["sessions"], "\n".join(f"- {s}" for s in sessions)),
        (words["capacity"], cap_text),
        (words["activities"], "\n".join(rows)),
        (words["out_of_scope"], "\n".join(f"- {s}" for s in scope)),
    ]
    text = "\n\n".join(f"### {heading}\n\n{content}" for heading, content in parts)
    return f"{text}\n\n{hidden(PLAN_MARK, plan)}\n"


def title(plan: dict) -> str:
    language = plan.get("language", "en")
    return f"{labels(language)['title']} · {plan['project']} · {show_date(plan['date'], language)}"


# --- closing


def check_closing(round_plan: dict) -> None:
    problems = []
    for a in round_plan["activities"]:
        if a.get("outcome") == "done":
            if not str(a.get("evidence", "")).strip():
                problems.append(f"{a['issue']}: done with no evidence")
        elif a.get("outcome") == "left-over":
            for field in ("state", "reason", "next_step"):
                if not str(a.get(field, "")).strip():
                    problems.append(f"{a['issue']}: left over with no {field}")
        else:
            problems.append(f"{a['issue']}: outcome is {a.get('outcome')!r}, not done or left-over")
    for item in round_plan.get("pending", []):
        for field in ("what", "recommend", "link"):
            if not str(item.get(field, "")).strip():
                problems.append(f"pending '{item.get('what', '?')}': no {field}")
    if problems:
        raise Refused("the closing is refused:\n  " + "\n  ".join(problems))


def closing(round_plan: dict, history: list[dict], week_last: bool) -> dict:
    check_closing(round_plan)
    language = round_plan.get("language", "en")
    words = labels(language)
    unit = round_plan.get("unit", "count")
    acts = round_plan["activities"]
    done = [a for a in acts if a["outcome"] == "done"]
    left = [a for a in acts if a["outcome"] == "left-over"]
    data = {
        "date": round_plan["date"],
        "planned": len(acts),
        "done": len(done),
        "points_planned": sum(SIZES[a["size"]] for a in acts),
        "points_done": sum(SIZES[a["size"]] for a in done),
        "capacity": round_plan.get("capacity"),
        "unit": unit,
        "left_over": [
            {k: a.get(k) for k in ("result", "issue", "owner", "done", "size", "rounds", "state", "reason", "next_step")}
            for a in left
        ],
    }
    rounds = closed_rounds(history) + [data]
    next_cap = capacity(rounds, unit)
    _, raised = carry_over(rounds)
    raised_issues = {a["issue"] for a in raised}
    comment = render_closing(round_plan, data, next_cap, raised, words)
    issue_comments = [
        {"issue": a["issue"], "close": True, "body": f"{words['closed_by'].format(round=round_plan['date'])}\n\n{words['evidence']}: {a['evidence']}"}
        for a in done
    ] + [
        {
            "issue": a["issue"],
            "close": False,
            "body": "\n".join(
                [
                    words["left_raised"].format(round=round_plan["date"], n=a["rounds"])
                    if a["issue"] in raised_issues
                    else words["left_by"].format(round=round_plan["date"]),
                    "",
                    f"- {words['state']}: {a['state']}",
                    f"- {words['reason']}: {a['reason']}",
                    f"- {words['next_step']}: {a['next_step']}",
                ]
            ),
        }
        for a in left
    ]
    result = {
        "closing": comment,
        "issue_comments": issue_comments,
        "slack": render_slack(round_plan, data, next_cap, words),
        "numbers": data,
        "next_capacity": next_cap,
    }
    if week_last:
        result["week"] = render_week(round_plan, rounds, words)
    return result


def render_closing(round_plan: dict, data: dict, next_cap: float | None, raised: list[dict], words: dict) -> str:
    acts = round_plan["activities"]
    delivered = [f"- {a['issue']} {a['result']} — {words['evidence']}: {a['evidence']}" for a in acts if a["outcome"] == "done"]
    left = [
        f"- {a['issue']} {a['result']} — {words['state']}: {a['state']}; {words['reason']}: {a['reason']}; {words['next_step']}: {a['next_step']}"
        for a in acts
        if a["outcome"] == "left-over"
    ]
    pending = [f"- {p['what']} {words['recommend']} {p['recommend']} {p['link']}" for p in round_plan.get("pending", [])]
    numbers = [
        "- " + words["done_of_planned"].format(done=data["done"], planned=data["planned"], rate=show_rate(data["done"], data["planned"])),
        "- " + words["carried_line"].format(n=len(left) - len(raised)),
    ]
    if data["unit"] == "points":
        numbers.append("- " + words["points_line"].format(done=data["points_done"], planned=data["points_planned"]))
    if next_cap is not None:
        numbers.append("- " + words["next_capacity"].format(cap=show_number(next_cap)))
    if raised:
        numbers.append("- " + words["raised_line"].format(items=", ".join(a["issue"] for a in raised)))
    nothing = f"- {words['nothing']}"
    sections = [
        (words["delivered"], delivered),
        (words["left_over"], left),
        (words["decisions"], [f"- {d}" for d in round_plan.get("decisions", [])]),
        (words["pending"], pending),
        (words["context"], [f"- {c}" for c in round_plan.get("context", [])]),
        (words["numbers"], numbers),
    ]
    text = "\n\n".join(f"### {heading}\n\n" + ("\n".join(lines) if lines else nothing) for heading, lines in sections)
    return f"{text}\n\n{hidden(DATA_MARK, data)}\n"


def render_slack(round_plan: dict, data: dict, next_cap: float | None, words: dict) -> str:
    acts = round_plan["activities"]
    language = round_plan.get("language", "en")
    delivered = ", ".join(a["issue"] for a in acts if a["outcome"] == "done") or words["nothing"]
    left = ", ".join(f"{a['issue']} ({a['state']})" for a in acts if a["outcome"] == "left-over") or words["nothing"]
    pending = round_plan.get("pending", [])
    first = f" — {pending[0]['what']}" if pending else ""
    lines = [
        words["slack_head"].format(
            project=round_plan["project"],
            date=show_date(round_plan["date"], language),
            done=data["done"],
            planned=data["planned"],
            rate=show_rate(data["done"], data["planned"]),
        ),
        words["slack_delivered"].format(items=delivered),
        words["slack_left"].format(items=left),
        words["slack_pending"].format(n=len(pending), first=first),
        words["slack_capacity"].format(cap=show_number(next_cap) if next_cap is not None else "-"),
    ]
    if round_plan.get("round_issue"):
        lines.append(words["slack_link"].format(link=round_plan["round_issue"]))
    return "\n".join(lines) + "\n"


def render_week(round_plan: dict, rounds: list[dict], words: dict) -> str:
    language = round_plan.get("language", "en")
    year, week, _ = date.fromisoformat(round_plan["date"]).isocalendar()
    this_week = [r for r in rounds if date.fromisoformat(r["date"]).isocalendar()[:2] == (year, week)]
    lines = [words["week_head"].format(week=week, project=round_plan["project"])]
    for r in this_week:
        cap = r.get("capacity")
        lines.append(
            words["week_row"].format(
                date=show_date(r["date"], language),
                rate=show_rate(r["done"], r["planned"]),
                done=r["done"],
                planned=r["planned"],
                cap=show_number(cap) if cap is not None else "-",
            )
        )
    oldest = sorted(rounds[-1].get("left_over", []), key=lambda a: -a.get("rounds", 1))[:3]
    if oldest:
        items = ", ".join(f"{a['issue']} ({words['round_n'].format(n=a['rounds'])})" for a in oldest)
        lines.append(words["week_oldest"].format(items=items))
    return "\n".join(lines) + "\n"


def post_decision(channel: str | None, instructions: Path | None) -> str:
    """Whether the Slack summary may go out without asking: only on a recorded standing ok."""
    if not channel:
        return "no channel given: nothing to post"
    if instructions and instructions.is_file():
        for line in instructions.read_text(encoding="utf-8").splitlines():
            if STANDING_OK in line and channel in line.split():
                return f"standing ok recorded for {channel} in {instructions}: post it"
    return f"no standing ok for {channel}: ask the person before posting"


# --- command line


def load(path: str | None) -> list | dict:
    if not path:
        return []
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_open(args: argparse.Namespace) -> int:
    result = opening(load(args.plan), load(args.history))
    plan = result["plan"]
    if args.body:
        Path(args.body).write_text(result["body"], encoding="utf-8")
    print(f"title: {title(plan)}")
    print(f"capacity: {show_number(plan['capacity']) if plan['capacity'] is not None else 'uncalibrated'}")
    for a in plan["activities"]:
        print(f"activity: {a['issue']} {a['origin']} round {a['rounds']} {a.get('state', '')}".rstrip())
    for a in result["raised"]:
        print(f"raise: {a['issue']} would enter round {a['rounds']}; ask the person to split, reassign or drop it")
    for warning in result["warnings"]:
        print(f"warning: {warning}")
    if not args.body:
        print()
        print(result["body"], end="")
    return 0


def run_extract(args: argparse.Namespace) -> int:
    plan = read_hidden(PLAN_MARK, Path(args.body).read_text(encoding="utf-8"))
    if plan is None:
        raise Refused(f"{args.body} carries no {PLAN_MARK} block; it was not opened by this script")
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


def run_close(args: argparse.Namespace) -> int:
    result = closing(load(args.plan), load(args.history), args.week_last)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "closing.md").write_text(result["closing"], encoding="utf-8")
    (out / "issue-comments.json").write_text(json.dumps(result["issue_comments"], ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "slack.txt").write_text(result["slack"], encoding="utf-8")
    if "week" in result:
        (out / "week.txt").write_text(result["week"], encoding="utf-8")
    data = result["numbers"]
    print(f"done: {data['done']} of {data['planned']} ({show_rate(data['done'], data['planned'])})")
    cap = result["next_capacity"]
    print(f"next capacity: {show_number(cap) if cap is not None else 'uncalibrated'}")
    print(f"slack: {post_decision(args.channel, Path(args.instructions) if args.instructions else None)}")
    print(f"written: {', '.join(sorted(p.name for p in out.iterdir()))} in {out}")
    return 0


def run_calibrate(args: argparse.Namespace) -> int:
    rounds = closed_rounds(load(args.history))
    for r in rounds:
        rate = completion(r)
        verdict = "" if rate is None else (" healthy" if HEALTHY[0] <= rate <= HEALTHY[1] else " outside 70-90%")
        print(f"round {r['date']}: {show_rate(r['done'], r['planned'])} ({r['done']}/{r['planned']}){verdict}")
    cap = capacity(rounds, args.unit)
    print(f"next capacity: {show_number(cap) if cap is not None else 'uncalibrated'} {args.unit}")
    carried, raised = carry_over(rounds)
    for a in carried:
        print(f"age: {a['issue']} enters round {a['rounds']}")
    for a in raised:
        print(f"age: {a['issue']} would enter round {a['rounds']}: raise it")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("open")
    p.add_argument("plan")
    p.add_argument("--history")
    p.add_argument("--body")
    p.set_defaults(run=run_open)
    p = sub.add_parser("extract")
    p.add_argument("body")
    p.set_defaults(run=run_extract)
    p = sub.add_parser("close")
    p.add_argument("plan")
    p.add_argument("--history")
    p.add_argument("--out", default="round-closing")
    p.add_argument("--week-last", action="store_true")
    p.add_argument("--channel")
    p.add_argument("--instructions")
    p.set_defaults(run=run_close)
    p = sub.add_parser("calibrate")
    p.add_argument("--history", required=True)
    p.add_argument("--unit", choices=["count", "points"], default="count")
    p.set_defaults(run=run_calibrate)
    args = parser.parse_args(argv)
    try:
        return args.run(args)
    except Refused as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
