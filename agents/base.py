"""In-memory, tamper-evident HMAC audit logging and best-effort identifier screening.

The identifier screening is not de-identification or HIPAA certification.
"""
import os
import re
import json
import time
import hmac
import hashlib
import secrets
from copy import deepcopy
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

PHI_PATTERNS = [
    re.compile(r"\b(?:MRN|mrn)[:#\s-]*\d{4,10}\b", re.IGNORECASE),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    re.compile(r"\b(?:DOB|Date of Birth)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", re.IGNORECASE),
    re.compile(r"\b(?:Patient\s+Name|Patient)[:\s]+[A-Z][a-z]+\s+[A-Z][a-z]+\b", re.IGNORECASE),
    re.compile(r"\b(?:John\s+Doe|Jane\s+Smith|Alice\s+Johnson)\b", re.IGNORECASE),
]

class SecurityException(Exception):
    """An identifier matched one of the screening patterns."""

class ResourceLimitExceededException(Exception):
    """A computation exceeded a configured bound."""

def assert_no_phi(text: str) -> None:
    for pattern in PHI_PATTERNS:
        if pattern.search(str(text)):
            raise SecurityException("Possible sensitive identifier detected")

class PHIGuard:
    @staticmethod
    def assert_no_phi(text: str) -> None:
        assert_no_phi(text)
    @staticmethod
    def redact_phi(text: str) -> str:
        res = str(text)
        for pattern in PHI_PATTERNS:
            res = pattern.sub("[REDACTED_IDENTIFIER]", res)
        return res

class AuditTrail:
    """In-memory chain of HMAC-SHA256 signed event metadata."""
    def __init__(self, secret_key: Optional[str] = None):
        key = secret_key or os.getenv("AUDIT_SECRET_KEY")
        if not key:
            import warnings
            warnings.warn("AUDIT_SECRET_KEY unset; using an ephemeral audit key and nonpersistent log.",
                          RuntimeWarning, stacklevel=2)
            key = secrets.token_hex(32)
        self.secret_key = key.encode("utf-8")
        self.logs: List[Dict[str, Any]] = []

    def _signature(self, entry: Dict[str, Any]) -> str:
        fields = ("audit_id", "timestamp", "actor", "actor_tier", "event_type", "payload_hash", "prev_hash")
        msg = "|".join(str(entry[field]) for field in fields)
        return hmac.new(self.secret_key, msg.encode("utf-8"), hashlib.sha256).hexdigest()

    def log(self, actor: str, actor_tier: str, event_type: str, details: Dict[str, Any]) -> Dict[str, Any]:
        payload = json.dumps(details, sort_keys=True, allow_nan=False)
        for element in (payload, actor, actor_tier, event_type):
            assert_no_phi(element)
        prev = self.logs[-1]["current_hash"] if self.logs else "GENESIS_BLOCK_0000000000000000"
        entry = {
            "audit_id": f"AUDIT-{int(time.time()*1000)}-{len(self.logs)+1}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "actor_tier": actor_tier,
            "event_type": event_type,
            "payload_hash": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            "prev_hash": prev,
        }
        entry["current_hash"] = self._signature(entry)
        self.logs.append(entry)
        return deepcopy(entry)

    def verify_integrity(self) -> bool:
        previous = "GENESIS_BLOCK_0000000000000000"
        for entry in self.logs:
            try:
                if entry["prev_hash"] != previous:
                    return False
                expected = self._signature(entry)
                if not hmac.compare_digest(expected, entry["current_hash"]):
                    return False
                previous = entry["current_hash"]
            except (KeyError, TypeError, ValueError):
                return False
        return True

    def get_trail(self) -> List[Dict[str, Any]]:
        return deepcopy(self.logs)

GLOBAL_AUDIT = AuditTrail()

class AuditLogger:
    @staticmethod
    def log(actor: str, actor_tier: str, event_type: str, details: Dict[str, Any]) -> Dict[str, Any]:
        return GLOBAL_AUDIT.log(actor, actor_tier, event_type, details)
    @staticmethod
    def get_trail() -> List[Dict[str, Any]]:
        return GLOBAL_AUDIT.get_trail()
    @staticmethod
    def verify_integrity() -> bool:
        return GLOBAL_AUDIT.verify_integrity()

class ActionExecutor:
    @staticmethod
    def execute_with_audit(actor: str, actor_tier: str, action_type: str, fn, *args, **kwargs):
        result = fn(*args, **kwargs)
        AuditLogger.log(actor, actor_tier, action_type, {"status": "SUCCESS"})
        return result
