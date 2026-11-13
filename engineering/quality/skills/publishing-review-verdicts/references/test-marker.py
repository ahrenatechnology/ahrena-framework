#!/usr/bin/env python3
"""Tests for marker.py: the contract of the review marker, as cases.

Each case is a marker a reader may meet. #274/AC-1 is the accepted grammar,
#274/AC-2 the markers a reader must refuse, #274/AC-3 the free prose around it.

Usage:
    python3 engineering/quality/skills/publishing-review-verdicts/references/test-marker.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location("marker", Path(__file__).resolve().parent / "marker.py")
marker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(marker)

FULL = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"

ACCEPTED = [
    ("<!-- ahrena-review:142:a1b2c3d verdict=approve -->", "approve"),
    (f"<!-- ahrena-review:142:{FULL} verdict=request-changes -->", "request-changes"),
    ("<!-- ahrena-review:7:a1b2c3d verdict=comment -->", "comment"),
]

REFUSED = [
    "<!-- ahrena-review:142:a1b2c3d -->",
    "<!-- ahrena-review:142:a1b2c3 verdict=approve -->",
    f"<!-- ahrena-review:142:{FULL}0 verdict=approve -->",
    "<!-- ahrena-review:142:A1B2C3D verdict=approve -->",
    "<!-- ahrena-review:142:a1b2c3d verdict=request_changes -->",
    "<!-- ahrena-review:142:a1b2c3d verdict=APPROVE -->",
    "<!-- ahrena-review:142:a1b2c3d verdict=approved -->",
    "<!-- ahrena-review:0142:a1b2c3d verdict=approve -->",
    "<!-- ahrena-review:142:a1b2c3d  verdict=approve -->",
    "## Argos review of a1b2c3d4: REQUEST CHANGES",
    "## Argos: approve (0 blocking)",
    "",
]


def check(name: str, ok: bool) -> bool:
    print(("ok   " if ok else "FAIL ") + name)
    return ok


def main() -> int:
    results = []
    for body, verdict in ACCEPTED:
        parsed = marker.parse(body)
        results.append(check(f"#274/AC-1 accepts {body}", bool(parsed) and parsed["verdict"] == verdict))
    for body in REFUSED:
        results.append(check(f"#274/AC-2 refuses {body!r}", marker.parse(body) is None))
    prose = "<!-- ahrena-review:142:a1b2c3d verdict=comment -->\n\n## Whatever title\n**Verdict:** approve"
    results.append(check("#274/AC-3 the prose below does not change the verdict", marker.parse(prose)["verdict"] == "comment"))
    results.append(check("#274/AC-3 a marker not on the first line is not read", marker.parse("title\n" + ACCEPTED[0][0]) is None))
    results.append(check("#274/AC-1 approves() matches the head by prefix", marker.approves(ACCEPTED[0][0], FULL)))
    results.append(check("#274/AC-1 approves() refuses another head", not marker.approves(ACCEPTED[0][0], "ffffffff" + FULL[8:])))
    results.append(check("#274/AC-2 approves() refuses a comment verdict", not marker.approves(ACCEPTED[2][0], FULL)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
