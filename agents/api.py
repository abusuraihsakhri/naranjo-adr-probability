"""FastAPI endpoints for causality scoring and existing operations workflows."""
from typing import Any, Dict
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from naranjo import calculate_score
from .base import AuditLogger, SecurityException
from .models import SystemTaskPayload
from .supervisor import SystemSupervisor
from .metrics import GLOBAL_METRICS

supervisor = SystemSupervisor(model_provider="mock")
app = FastAPI(
    title="Naranjo ADR Probability API",
    description="Ten-item Naranjo causality scale and separate demonstration operations endpoints.",
    version="1.1.0",
)

class ChatRequest(BaseModel):
    query: str

class NaranjoRequest(BaseModel):
    responses: Dict[str, Any]

@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "naranjo-adr-probability", "version": "1.1.0"}

@app.post("/api/naranjo")
def api_naranjo(payload: NaranjoRequest):
    """Calculate the ten-item Naranjo score; unknown must be explicit."""
    try:
        return calculate_score(payload.responses)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.get("/metrics")
def metrics():
    GLOBAL_METRICS.audit_blocks_total = len(AuditLogger.get_trail())
    return Response(
        content=GLOBAL_METRICS.export_prometheus_text(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )

@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    return supervisor.process_task(payload).to_dict()

@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        return {"response": supervisor.query_supervisory_chat(req.query)}
    except SecurityException as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
