#!/usr/bin/env python3
"""Naranjo adverse drug reaction probability scale (ten-question form).

Point values follow the NCBI LiverTox published questionnaire. This is a
causality aid, not an ADR severity or treatment decision scale.
"""
import argparse
import csv
import json
import os
import sys
from typing import Any, Dict, List, Optional

# (key, question, yes points, no points); unknown always contributes zero.
QUESTIONS = (
    ("q1", "Previous conclusive reports of this reaction?", 1, 0),
    ("q2", "Adverse event appeared after the suspected drug was given?", 2, -1),
    ("q3", "Reaction improved after withdrawal or a specific antagonist?", 1, 0),
    ("q4", "Reaction reappeared after readministration?", 2, -1),
    ("q5", "Other causes could independently explain the reaction?", -1, 2),
    ("q6", "Reaction reappeared after placebo administration?", -1, 1),
    ("q7", "Drug detected at toxic concentration in blood or other fluids?", 1, 0),
    ("q8", "Reaction changed in severity with a change in dose?", 1, 0),
    ("q9", "Similar reaction to same or related drug on previous exposure?", 1, 0),
    ("q10", "Adverse event supported by objective evidence?", 1, 0),
)
QUESTION_IDS = tuple(q[0] for q in QUESTIONS)


def _answer(value: Any) -> str:
    """Normalize explicit yes/no/unknown responses; reject ambiguous values."""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if value is None:
        return "unknown"
    if isinstance(value, str):
        norm = value.strip().lower()
        if norm in ("yes", "y"):
            return "yes"
        if norm in ("no", "n"):
            return "no"
        if norm in ("unknown", "do not know", "don't know", "not known", "na", "n/a"):
            return "unknown"
    raise ValueError(f"Invalid response {value!r}; use yes, no, or unknown")


def calculate_score(responses: Dict[str, Any]) -> Dict[str, Any]:
    """Score q1..q10 answers. Explicit unknown scores zero; missing is an error."""
    if not isinstance(responses, dict):
        raise TypeError("responses must be a dictionary")
    missing = [key for key in QUESTION_IDS if key not in responses]
    if missing:
        raise ValueError("Missing Naranjo answers: " + ", ".join(missing))
    detail = {}
    score = 0
    for key, question, yes_points, no_points in QUESTIONS:
        answer = _answer(responses[key])
        points = {"yes": yes_points, "no": no_points, "unknown": 0}[answer]
        detail[key] = {"question": question, "answer": answer, "points": points}
        score += points
    category = "definite" if score >= 9 else "probable" if score >= 5 else "possible" if score >= 1 else "doubtful"
    return {"score": score, "category": category, "detail": detail}


def assess_row(row: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(row, dict):
        raise TypeError("row must be a dictionary")
    return calculate_score({str(k).strip().lower(): v for k, v in row.items() if k is not None})


def process_csv(inp: str, out: str) -> List[Dict[str, Any]]:
    """Read q1..q10 CSV columns and write results after input validation."""
    if os.path.realpath(inp) == os.path.realpath(out):
        raise ValueError("Input and output must be different files")
    with open(inp, encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        normalized = [h.strip().lower() for h in headers]
        if len(normalized) != len(set(normalized)):
            raise ValueError("Duplicate CSV column names")
        missing = set(QUESTION_IDS) - set(normalized)
        if missing:
            raise ValueError("Missing CSV columns: " + ", ".join(sorted(missing)))
        if any(h in normalized for h in ("score", "category", "detail")):
            raise ValueError("Input CSV already contains output columns")
        results = []
        for line_no, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"CSV row {line_no} has more cells than headers")
            try:
                scored = assess_row(row)
            except ValueError as exc:
                raise ValueError(f"CSV row {line_no}: {exc}") from exc
            results.append({**row, "score": scored["score"], "category": scored["category"],
                            "detail": ";".join(f"{k}:{v['points']:+d}" for k, v in scored["detail"].items())})
    with open(out, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers + ["score", "category", "detail"])
        writer.writeheader()
        writer.writerows(results)
    return results


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="10-question Naranjo ADR causality assessment")
    commands = parser.add_subparsers(dest="command", required=True)
    single = commands.add_parser("single", help="Score a single case")
    single.add_argument("--json", help="JSON object with q1 through q10 answers")
    for key in QUESTION_IDS:
        single.add_argument(f"--{key}", choices=("yes", "no", "unknown"))
    batch = commands.add_parser("batch", help="Score CSV with q1 through q10 columns")
    batch.add_argument("--input", required=True)
    batch.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "single":
            if args.json and any(getattr(args, key) is not None for key in QUESTION_IDS):
                raise ValueError("Use either --json or --q1..--q10, not both")
            responses = json.loads(args.json) if args.json is not None else {k: getattr(args, k) for k in QUESTION_IDS if getattr(args, k) is not None}
            print(json.dumps(calculate_score(responses), indent=2))
        else:
            rows = process_csv(args.input, args.output)
            print(f"Scored {len(rows)} cases -> {args.output}")
        return 0
    except (TypeError, ValueError, OSError, csv.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
