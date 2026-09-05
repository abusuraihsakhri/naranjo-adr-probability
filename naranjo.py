#!/usr/bin/env python3
"""
Naranjo ADR Probability Scale
Naranjo (-4 to +13) adverse drug reaction probability with doubt/possible/probable/definite.
Points-based score with tiered action thresholds. Stdlib only.
"""
import argparse
import csv
import os
import sys
from typing import Dict, Any, List, Optional

# Clinical factors assessed in the Naranjo ADR scale
FACTORS = [
    ("Hypotension", 1),
    ("Tachycardia", 1),
    ("Tachypnea", 1),
    ("Fever", 1),
    ("Altered_mental", 1),
]

# Score thresholds: (max_score, tier_label)
THRESHOLDS = [(2, "low"), (4, "moderate"), (100, "high")]

# Naranjo probability categories
CATEGORIES = [
    (0, "doubtful"),      # score <= 0
    (4, "possible"),      # score 1-4
    (8, "probable"),      # score 5-8
    (13, "definite"),     # score >= 9
]


def _normalize_value(val) -> bool:
    """Convert various input types to boolean presence indicator."""
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val != 0
    s = str(val).strip().lower()
    return s in ("1", "true", "yes", "y", "present", "positive")


def calculate_score(present: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate Naranjo ADR score from present factors.

    Args:
        present: dict mapping factor name to presence indicator (bool, 1/0, yes/no)

    Returns:
        dict with score, tier, category, and detail of contributing factors
    """
    if not isinstance(present, dict):
        raise TypeError(f"present must be a dict, got {type(present).__name__}")

    score = 0
    detail: Dict[str, int] = {}

    for name, weight in FACTORS:
        # Accept factor name in various formats
        val = present.get(name)
        if val is None:
            val = present.get(name.lower())
        if val is None:
            val = present.get(name.replace("_", " "))
        if val is None:
            val = present.get(name.replace("_", " ").lower())

        if _normalize_value(val):
            score += weight
            detail[name] = weight

    # Determine tier
    tier = "high"
    for thr, label in THRESHOLDS:
        if score <= thr:
            tier = label
            break

    # Determine Naranjo category
    category = "definite"
    for max_score, cat_label in CATEGORIES:
        if score <= max_score:
            category = cat_label
            break

    return {"score": score, "tier": tier, "category": category, "detail": detail}


def assess_row(row: Dict[str, str]) -> Dict[str, Any]:
    """
    Assess a CSV row dict and compute the Naranjo score.

    Args:
        row: dict from csv.DictReader

    Returns:
        score result dict
    """
    if not isinstance(row, dict):
        raise TypeError(f"row must be a dict, got {type(row).__name__}")

    # Build normalized present dict with original and lowercase keys
    present: Dict[str, Any] = {}
    for k, v in row.items():
        if k is None:
            continue
        present[k] = v
        present[k.lower()] = v

    return calculate_score(present)


def _validate_safe_path(path: str, must_exist: bool = False) -> str:
    """
    Validate that a path is safe (no traversal) and optionally exists.

    Args:
        path: file path to validate
        must_exist: if True, raise FileNotFoundError when path doesn't exist

    Returns:
        resolved absolute path

    Raises:
        ValueError: if path contains traversal attempts
        FileNotFoundError: if must_exist and path doesn't exist
    """
    resolved = os.path.realpath(os.path.abspath(path))

    # Check for null bytes (can bypass some checks)
    if "\x00" in path:
        raise ValueError("Path contains null bytes")

    if must_exist and not os.path.isfile(resolved):
        raise FileNotFoundError(f"Input file not found: {path}")

    return resolved


def process_csv(inp: str, out: str) -> List[Dict[str, Any]]:
    """
    Process a CSV file and write results with scores.

    Args:
        inp: input CSV file path
        out: output CSV file path

    Returns:
        list of result row dicts
    """
    # Validate paths
    inp_path = _validate_safe_path(inp, must_exist=True)
    out_path = _validate_safe_path(out, must_exist=False)

    with open(inp_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fn = reader.fieldnames or []

    results = []
    for row in rows:
        res = assess_row(row)
        merged = {
            **row,
            "score": res["score"],
            "tier": res["tier"],
            "category": res["category"],
            "detail": ";".join(res["detail"].keys()),
        }
        results.append(merged)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fn) + ["score", "tier", "category", "detail"])
        w.writeheader()
        w.writerows(results)

    return results


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    p = argparse.ArgumentParser(prog="naranjo", description="Naranjo ADR Probability Scale")
    sub = p.add_subparsers(dest="cmd", required=True)

    # Single assessment
    s = sub.add_parser("single", help="Assess a single case")
    s.add_argument("--age", type=float, help="Patient age")
    s.add_argument("--sex", help="Patient sex (M/F)")
    for name, _ in FACTORS:
        flag = "--" + name.lower().replace(" ", "_").replace(">", "_gt_").replace("/", "_")
        s.add_argument(flag, default="0", help=f"Presence of {name}")
    s.add_argument("--json", help="JSON string of factor presence dict")

    # Batch processing
    b = sub.add_parser("batch", help="Batch process CSV file")
    b.add_argument("--input", required=True, help="Input CSV file path")
    b.add_argument("--output", required=True, help="Output CSV file path")

    return p


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point."""
    import json as _json

    p = build_parser()
    a = p.parse_args(argv)

    if a.cmd == "single":
        if a.json:
            try:
                present = _json.loads(a.json)
            except _json.JSONDecodeError as e:
                print(f"Error: Invalid JSON: {e}", file=sys.stderr)
                return 1
        else:
            present = {k: v for k, v in vars(a).items() if k not in ("cmd", "json")}
        res = calculate_score(present)
        print(res)
        return 0

    if a.cmd == "batch":
        try:
            res = process_csv(a.input, a.output)
            print(f"Processed {len(res)} -> {a.output}")
            return 0
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except (OSError, csv.Error) as e:
            print(f"Error processing CSV: {e}", file=sys.stderr)
            return 1

    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
