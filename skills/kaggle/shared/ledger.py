"""A local, append-only record of what was submitted and how it scored.

The file is ``./.kaggle-skill/ledger.jsonl`` in the folder the command runs
in (``KAGGLE_SKILL_DIR`` moves it). Each line is one JSON object:

- ``event: "submit"``: a submission that was sent, with the file's size and
  SHA-256, the message, and the score that was expected, if one was given.
- ``event: "score"``: what Kaggle reported for a submission later.

Lines are only ever added. Nothing here is sent anywhere.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared import script

FILE_NAME = "ledger.jsonl"


def path() -> Path:
    return script.state_dir() / FILE_NAME


def file_facts(file: Path) -> dict[str, Any]:
    """Name, size and SHA-256 of a submission file."""
    digest = hashlib.sha256()
    size = 0
    with open(file, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return {"file": str(file), "bytes": size, "sha256": digest.hexdigest()}


def append(row: dict[str, Any]) -> Path:
    """Add one line to the ledger and return the ledger's path.

    Raises OSError when the line cannot be written, a link on the way included.
    """
    record = {"time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **row}
    line = json.dumps(record, ensure_ascii=False) + "\n"
    return script.write_state(path(), line, append=True)


def read() -> list[dict[str, Any]]:
    """Every readable line, oldest first. A damaged line is skipped."""
    try:
        lines = path().read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def submissions(competition: str | None = None) -> list[dict[str, Any]]:
    """Each recorded submission with the latest score recorded for it."""
    rows = read()
    scores: dict[Any, dict[str, Any]] = {}
    for row in rows:
        if row.get("event") == "score" and row.get("ref") is not None:
            scores[row["ref"]] = row
    merged = []
    recorded = set()
    for row in rows:
        if row.get("event") != "submit":
            continue
        recorded.add(row.get("ref"))
        if competition and row.get("competition") != competition:
            continue
        item = dict(row)
        score = scores.get(row.get("ref")) if row.get("ref") is not None else None
        if score:
            item["status"] = score.get("status")
            item["public_score"] = score.get("public_score")
            item["scored_at"] = score.get("time")
        merged.append(item)
    # A score that was watched for a submission made some other way.
    for ref, score in scores.items():
        if ref in recorded or (competition and score.get("competition") != competition):
            continue
        merged.append({**score, "scored_at": score.get("time")})
    merged.sort(key=lambda item: str(item.get("time") or ""))
    return merged


def expected_for(ref: Any) -> float | None:
    """The score that was expected for a submission, if one was recorded."""
    for row in reversed(read()):
        if row.get("event") == "submit" and row.get("ref") == ref:
            value = row.get("expected")
            return float(value) if isinstance(value, (int, float)) else None
    return None


def has_score(ref: Any) -> bool:
    return any(row.get("event") == "score" and row.get("ref") == ref for row in read())
