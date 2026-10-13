"""HMAC audit-chain tamper detection and defensive-copy behavior."""
from agents.base import AuditTrail

def test_audit_verification_and_mutation_isolation():
    trail = AuditTrail(secret_key="test-only-long-secret")
    first = trail.log("unit", "tester", "EVENT", {"status": "OK"})
    second = trail.log("unit", "tester", "EVENT_2", {"status": "OK"})
    assert trail.verify_integrity()
    first["actor"] = "tampered"
    second["current_hash"] = "tampered"
    external = trail.get_trail()
    external[0]["actor"] = "tampered"
    assert trail.verify_integrity()
    assert trail.get_trail()[0]["actor"] == "unit"

def test_mutated_signed_fields_are_detected():
    trail = AuditTrail(secret_key="test-only-long-secret")
    trail.log("unit", "tester", "EVENT", {"status": "OK"})
    trail.logs[0]["actor"] = "attacker"
    assert not trail.verify_integrity()

def test_mutated_hash_is_detected():
    trail = AuditTrail(secret_key="test-only-long-secret")
    trail.log("unit", "tester", "EVENT", {"status": "OK"})
    trail.log("unit", "tester", "NEXT", {"status": "OK"})
    trail.logs[0]["current_hash"] = "0" * 64
    assert not trail.verify_integrity()
