"""Read token usage out of a Claude Code transcript or a claude-code-action execution file.

Two input adapters, one result. `read_session` streams a session transcript and the
transcripts of the sub-agents it started, one line at a time. `read_execution` reads the JSON
array `anthropics/claude-code-action` leaves behind.

Only structural fields are read: record type, ids, timestamps, the working directory and
branch a record was written under, the model id and the usage counters. No prompt, response,
tool input, tool output or file content is kept, and none leaves this module.

What the transcripts taught, and the code depends on:

- One API response is written as several records, one per content block, all carrying the
  same `message.id`. Summing records counts a response several times. Usage is therefore
  folded per message id, taking the largest value seen for each counter.
- In a sub-agent transcript most records carry the usage snapshot taken when the response
  started, with `stop_reason` null and a placeholder `output_tokens`. Those responses are
  counted in `unfinished`, so a report can say their output is a lower bound.
- Each record carries `cwd` and `gitBranch`, and a session moves between them. Usage is kept
  per (cwd, branch) segment, not per session.
- Timestamps are not strictly ordered inside a file, so active time is computed over the
  sorted timeline of every event of the session, sub-agents included.

Standard library only.
"""

from __future__ import annotations

import json
from array import array
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

KINDS = ("input", "output", "cache_write_5m", "cache_write_1h", "cache_read")
FAST_SUFFIX = ":fast"
US_SUFFIX = ":us"


def empty_tokens() -> dict[str, int]:
    return dict.fromkeys(KINDS, 0)


def add_tokens(total: dict[str, dict[str, int]], model: str, counts: dict[str, int]) -> None:
    """Add one model's counters into a tokens-by-model map."""
    bucket = total.setdefault(model, empty_tokens())
    for kind in KINDS:
        bucket[kind] += int(counts.get(kind, 0))


def merge_tokens(total: dict[str, dict[str, int]], other: dict[str, dict[str, int]]) -> None:
    for model, counts in other.items():
        add_tokens(total, model, counts)


def sum_kinds(tokens: dict[str, dict[str, int]]) -> dict[str, int]:
    """Tokens by kind, across every model."""
    out = empty_tokens()
    for counts in tokens.values():
        for kind in KINDS:
            out[kind] += int(counts.get(kind, 0))
    return out


def parse_time(value: object) -> float | None:
    """An ISO-8601 timestamp as epoch seconds, or None when it is not one."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def counters(usage: dict) -> dict[str, int]:
    """The five kinds out of an API usage object.

    A cache write whose time-to-live is not broken down is counted as a 5-minute write, which
    is the cheaper of the two and so the lower bound.
    """
    written = int(usage.get("cache_creation_input_tokens") or 0)
    split = usage.get("cache_creation")
    hour = int(split.get("ephemeral_1h_input_tokens") or 0) if isinstance(split, dict) else 0
    hour = min(hour, written) if written else hour
    return {
        "input": int(usage.get("input_tokens") or 0),
        "output": int(usage.get("output_tokens") or 0),
        "cache_write_5m": max(written - hour, 0),
        "cache_write_1h": hour,
        "cache_read": int(usage.get("cache_read_input_tokens") or 0),
    }


def model_key(model: str, usage: dict, tiers: dict) -> str:
    """The price-table key of a response: the model id, plus the variant it was billed under.

    A variant is anything the price list prices apart: a prompt over a model's size tier, fast
    mode, US-only inference. Keeping it in the key means a variant with no entry in the price
    table is reported as unpriced instead of being priced as the standard one.
    """
    key = model
    tier = tiers.get(model)
    if isinstance(tier, dict):
        prompt = sum(int(usage.get(name) or 0) for name in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
        if prompt > int(tier.get("over_tokens", 0)):
            key = str(tier.get("key", model))
    if usage.get("speed") == "fast":
        key += FAST_SUFFIX
    if usage.get("inference_geo") == "us":
        key += US_SUFFIX
    return key


@dataclass
class Segment:
    """What a session did under one working directory and branch."""

    cwd: str
    branch: str
    tokens: dict[str, dict[str, int]] = field(default_factory=dict)
    turns: int = 0
    responses: int = 0
    unfinished: int = 0
    first: float | None = None
    last: float | None = None
    active: float = 0.0
    intervals: list[list[float]] = field(default_factory=list)

    def touch(self, moment: float) -> None:
        self.first = moment if self.first is None else min(self.first, moment)
        self.last = moment if self.last is None else max(self.last, moment)


@dataclass
class Response:
    """One API response, folded over the records that repeat it."""

    segment: int
    model: str
    counts: dict[str, int]
    finished: bool


@dataclass
class Reading:
    """Everything read from one session, before it is priced or attributed."""

    segments: list[Segment] = field(default_factory=list)
    index: dict[tuple[str, str], int] = field(default_factory=dict)
    responses: dict[str, Response] = field(default_factory=dict)
    times: array = field(default_factory=lambda: array("d"))
    owners: array = field(default_factory=lambda: array("l"))
    subagents: int = 0
    active: float = 0.0

    def segment(self, cwd: str, branch: str) -> int:
        key = (cwd, branch)
        if key not in self.index:
            self.index[key] = len(self.segments)
            self.segments.append(Segment(cwd, branch))
        return self.index[key]


def span(reading: Reading) -> tuple[float | None, float | None]:
    """The first and the last event of a reading."""
    return (min(reading.times), max(reading.times)) if reading.times else (None, None)


def is_prompt(record: dict) -> bool:
    """True for a record that is a person's turn, judged by its shape and never by its text."""
    if record.get("type") != "user" or record.get("isSidechain") or record.get("isMeta"):
        return False
    if record.get("isCompactSummary") or "toolUseResult" in record or "sourceToolAssistantUUID" in record:
        return False
    message = record.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, list):
        return not any(isinstance(block, dict) and block.get("type") == "tool_result" for block in content)
    return isinstance(content, str)


def fold_response(reading: Reading, record: dict, owner: int, tiers: dict) -> None:
    """Fold one assistant record into the response it repeats."""
    message = record.get("message")
    usage = message.get("usage") if isinstance(message, dict) else None
    if not isinstance(usage, dict):
        return
    counts = counters(usage)
    if not any(counts.values()):
        return
    identity = str(message.get("id") or record.get("uuid") or len(reading.responses))
    finished = message.get("stop_reason") is not None
    seen = reading.responses.get(identity)
    if seen is None:
        key = model_key(str(message.get("model") or "unknown"), usage, tiers)
        reading.responses[identity] = Response(owner, key, counts, finished)
        return
    for kind in KINDS:
        seen.counts[kind] = max(seen.counts[kind], counts[kind])
    seen.finished = seen.finished or finished


def read_record(reading: Reading, record: dict, owner: int, tiers: dict) -> int:
    """Take what one transcript record contributes; return the segment it belongs to."""
    if "cwd" in record or "gitBranch" in record:
        owner = reading.segment(str(record.get("cwd") or ""), str(record.get("gitBranch") or ""))
    moment = parse_time(record.get("timestamp"))
    if moment is not None:
        reading.times.append(moment)
        reading.owners.append(owner)
        reading.segments[owner].touch(moment)
    if record.get("type") == "assistant":
        fold_response(reading, record, owner, tiers)
    elif is_prompt(record):
        reading.segments[owner].turns += 1
    return owner


def read_transcript(reading: Reading, path: Path, tiers: dict) -> None:
    """Stream one transcript file into the reading, a line at a time."""
    owner = reading.segment("", "")
    with path.open(encoding="utf-8", errors="replace") as lines:
        for line in lines:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict):
                owner = read_record(reading, record, owner, tiers)


def settle_responses(reading: Reading) -> None:
    """Move the folded responses into their segments."""
    for response in reading.responses.values():
        segment = reading.segments[response.segment]
        add_tokens(segment.tokens, response.model, response.counts)
        segment.responses += 1
        segment.unfinished += 0 if response.finished else 1
    reading.responses = {}


def settle_activity(reading: Reading, idle: float) -> None:
    """Active time: every gap between consecutive events that is at most the idle threshold.

    The gap is credited to the segment of the event that ends it, and kept as an interval so
    a report can take the union across sessions that ran at the same time.
    """
    order = sorted(range(len(reading.times)), key=reading.times.__getitem__)
    for before, after in zip(order, order[1:]):
        start, end = reading.times[before], reading.times[after]
        if end - start > idle:
            continue
        segment = reading.segments[reading.owners[after]]
        segment.active += end - start
        reading.active += end - start
        if segment.intervals and segment.intervals[-1][1] >= start:
            segment.intervals[-1][1] = end
        else:
            segment.intervals.append([start, end])


def subagent_transcripts(transcript: Path) -> list[Path]:
    """The transcripts of the sub-agents a session started.

    Claude Code writes them beside the session's own file, under a directory named after the
    session: `<session>.jsonl` and `<session>/subagents/agent-<id>.jsonl`.
    """
    folder = transcript.with_suffix("") / "subagents"
    return sorted(folder.glob("*.jsonl")) if folder.is_dir() else []


def read_session(transcript: Path, idle: float, tiers: dict) -> Reading:
    """Read a session and its sub-agents into segments with tokens, turns and time."""
    reading = Reading()
    read_transcript(reading, transcript, tiers)
    for path in subagent_transcripts(transcript):
        read_transcript(reading, path, tiers)
        reading.subagents += 1
    settle_responses(reading)
    settle_activity(reading, idle)
    reading.segments = [segment for segment in reading.segments if segment.tokens or segment.turns]
    return reading


@dataclass
class Execution:
    """What a claude-code-action execution file says about one run."""

    tokens: dict[str, dict[str, int]] = field(default_factory=dict)
    source: str = "none"
    first: float | None = None
    last: float | None = None
    duration: float | None = None
    turns: int | None = None
    reported_cost: float | None = None
    session_id: str | None = None


def result_tokens(result: dict, hour_writes: dict[str, int]) -> dict[str, dict[str, int]]:
    """Tokens by model from the result message's `modelUsage`, which covers sub-agents.

    `modelUsage` gives one cache-write figure with no time-to-live. The part the run's own
    messages show as a 1-hour write is kept as one; the rest is counted as a 5-minute write.
    """
    tokens: dict[str, dict[str, int]] = {}
    usage = result.get("modelUsage")
    for model, entry in (usage.items() if isinstance(usage, dict) else ()):
        if not isinstance(entry, dict):
            continue
        written = int(entry.get("cacheCreationInputTokens") or 0)
        hour = min(written, hour_writes.get(model, 0))
        add_tokens(tokens, str(model), {
            "input": int(entry.get("inputTokens") or 0),
            "output": int(entry.get("outputTokens") or 0),
            "cache_write_5m": written - hour,
            "cache_write_1h": hour,
            "cache_read": int(entry.get("cacheReadInputTokens") or 0),
        })
    return {model: counts for model, counts in tokens.items() if any(counts.values())}


def message_tokens(messages: list, tiers: dict) -> tuple[dict[str, dict[str, int]], list[float]]:
    """Tokens by model from the assistant messages of an execution file, and their timestamps."""
    reading = Reading()
    owner = reading.segment("", "")
    for message in messages:
        if isinstance(message, dict) and message.get("type") == "assistant":
            fold_response(reading, message, owner, tiers)
        moment = parse_time(message.get("timestamp")) if isinstance(message, dict) else None
        if moment is not None:
            reading.times.append(moment)
    moments = list(reading.times)
    settle_responses(reading)
    return reading.segments[owner].tokens, moments


def read_execution(path: Path, tiers: dict) -> Execution:
    """Read the execution file of one claude-code-action run.

    The file is one JSON array of the run's SDK messages. The last `result` message carries
    `modelUsage`, which the Agent SDK documents as covering the main loop and sub-agents; when
    it is there it is the source. Without it the assistant messages are summed, which leaves
    output tokens as a lower bound and can miss sub-agents, and `source` says so.
    """
    messages = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(messages, list):
        raise ValueError("the execution file is not a JSON array of messages")
    summed, moments = message_tokens(messages, tiers)
    results = [m for m in messages if isinstance(m, dict) and m.get("type") == "result"]
    result = results[-1] if results else {}
    run = Execution(first=min(moments, default=None), last=max(moments, default=None))
    hour_writes = {model: counts["cache_write_1h"] for model, counts in summed.items()}
    run.tokens = result_tokens(result, hour_writes)
    run.source = "result.modelUsage" if run.tokens else "assistant-messages"
    run.tokens = run.tokens or summed
    if isinstance(result.get("duration_ms"), (int, float)):
        run.duration = result["duration_ms"] / 1000
    run.turns = result.get("num_turns") if isinstance(result.get("num_turns"), int) else None
    cost = result.get("total_cost_usd")
    run.reported_cost = float(cost) if isinstance(cost, (int, float)) else None
    run.session_id = next((str(m["session_id"]) for m in messages if isinstance(m, dict) and m.get("session_id")), None)
    return run
