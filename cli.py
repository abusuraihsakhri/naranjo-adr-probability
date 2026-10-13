"""
Command Line Interface for Naranjo Adr Probability.
"""
import argparse
import csv
import json
import sys
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor
from agents.base import AuditLogger

supervisor = SystemSupervisor(model_provider="mock")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="naranjo-adr-probability", description="Naranjo Adr Probability")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Audit
    p_audit = subparsers.add_parser("audit", help="Run single task evaluation")
    p_audit.add_argument("--task-id", default="TASK-2026-001")
    p_audit.add_argument("--target", default="KEY-TARGET-01")
    p_audit.add_argument("--primary", type=float, default=28.5)
    p_audit.add_argument("--secondary", type=float, default=14.2)
    p_audit.add_argument("--critical", action="store_true")
    p_audit.add_argument("--status", default="DISCORDANT")

    # Chat
    p_chat = subparsers.add_parser("chat", help="System configuration query")
    p_chat.add_argument("query", nargs="+")

    # Batch
    p_batch = subparsers.add_parser("batch", help="Batch process CSV records")
    p_batch.add_argument("-i", "--input", required=True)
    p_batch.add_argument("-o", "--output", default="results.csv")

    # Verify Audit
    subparsers.add_parser("verify-audit", help="Verify HMAC audit trail integrity")

    # Serve
    p_serve = subparsers.add_parser("serve", help="Launch FastAPI REST server")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)

    if args.command == "audit":
        payload = SystemTaskPayload(
            task_id=args.task_id,
            target_identifier=args.target,
            primary_metric=args.primary,
            secondary_metric=args.secondary,
            status_descriptor=args.status,
            is_critical_flag=args.critical,
        )
        dossier = supervisor.process_task(payload)
        print("=" * 80)
        print(f"  NARANJO ADR PROBABILITY")
        print(f"  Domain: Clinical & Biomedical AI | Standard: CAP / CLSI / ISO Standards")
        print(f"  Dossier ID: {dossier.dossier_id} | Urgency: [{dossier.overall_urgency.value}]")
        print("=" * 80)
        for a in dossier.alerts:
            print(f"\n  [{a.urgency.value}] from {a.origin_worker}:")
            print(f"  Summary: {a.summary}")
            print(f"  Details: {a.technical_details}")
            print(f"  Action:  {a.actionable_remediation}")
        print(f"\n  HMAC-SHA256 Audit Hash: {dossier.audit_hash}")
        print("=" * 80)
        return 0

    if args.command == "chat":
        ans = supervisor.query_supervisory_chat(" ".join(args.query))
        print(f"\n[Naranjo Adr Probability Supervisor]:\n{ans}\n")
        return 0

    if args.command == "verify-audit":
        trail = AuditLogger.get_trail()
        valid = AuditLogger.verify_integrity()
        print(f"Audit Trail Blocks: {len(trail)} | Cryptographic Integrity Verified: {valid}")
        return 0

    if args.command == "batch":
        import os

        def parse_flag(value):
            text = str(value if value is not None else "false").strip().lower()
            if text in ("true", "1", "yes", "y"):
                return True
            if text in ("false", "0", "no", "n", ""):
                return False
            raise ValueError(f"Invalid is_critical_flag: {value!r}")

        try:
            if "\x00" in args.input or "\x00" in args.output:
                raise ValueError("Invalid file path")
            if os.path.realpath(args.input) == os.path.realpath(args.output):
                raise ValueError("Input and output must differ")
            with open(args.input, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                fieldnames = list(reader.fieldnames or [])
                rows = list(reader)
            out_fields = ["overall_urgency", "integrity_status", "total_alerts", "audit_hash"]
            if any(name in fieldnames for name in out_fields):
                raise ValueError("Input CSV already contains output columns")
            if any(None in row for row in rows):
                raise ValueError("A CSV row has more cells than the header")
            out_rows = []
            for r in rows:
                payload = SystemTaskPayload(
                    task_id=r.get("task_id") or "TASK-01",
                    target_identifier=r.get("target_identifier") or "TARGET-01",
                    primary_metric=float(r.get("primary_metric") or 15.0),
                    secondary_metric=float(r.get("secondary_metric") or 5.0),
                    status_descriptor=r.get("status_descriptor") or "NOMINAL",
                    is_critical_flag=parse_flag(r.get("is_critical_flag")),
                )
                dossier = supervisor.process_task(payload)
                out_rows.append({**r, "overall_urgency": dossier.overall_urgency.value,
                                 "integrity_status": dossier.integrity_status.value,
                                 "total_alerts": dossier.total_alerts,
                                 "audit_hash": dossier.audit_hash})
            with open(args.output, mode="w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames + out_fields)
                writer.writeheader()
                writer.writerows(out_rows)
            print(f"Processed {len(out_rows)} records -> {args.output}")
            return 0
        except (OSError, ValueError, csv.Error) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    if args.command == "serve":
        import uvicorn
        from agents.api import app
        print(f"Starting Naranjo Adr Probability API server on http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
