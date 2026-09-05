# Naranjo ADR Probability

> **Domain:** Clinical Decision Support & Biomedical Computing

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)

</div>

---

## What It Does

Naranjo ADR Probability Scale calculator. Implements the Naranjo algorithm (-4 to +13) for assessing adverse drug reaction probability with categories: doubtful / possible / probable / definite. Points-based scoring with tiered action thresholds.

---

## Project Structure

```
naranjo-adr-probability/
├── naranjo.py          # Core scoring algorithm (stdlib only)
├── cli.py              # Multi-command CLI (audit, chat, batch, serve)
├── enrichment.py       # Longitudinal tracking, EHR/FHIR, reporting modules
├── simulator.py        # High-throughput batch simulation
├── agents/
│   ├── base.py         # PHI guard, HMAC-SHA256 audit trail
│   ├── models.py       # Pydantic schemas
│   ├── supervisor.py   # Multi-agent orchestrator
│   ├── workers.py      # QC, Safety, Protocol conformance workers
│   ├── api.py          # FastAPI REST server
│   ├── metrics.py      # Prometheus metrics exporter
│   ├── learning.py     # Bayesian calibration engine
│   ├── llm_factory.py  # LLM provider abstraction
│   └── streamer.py     # WebSocket telemetry broadcaster
├── tests/              # Pytest test suite
├── web/index.html      # Operations console UI
├── Dockerfile
└── docker-compose.yml
---

## Installation

```bash
pip install -e ".[dev]"
```

---

## Usage

### 1. Single Case Assessment

```bash
# Using CLI flags
python naranjo.py single --hypotension 1 --tachycardia 1

# Using JSON input
python naranjo.py single --json '{"Hypotension": true, "Fever": true}'
```

### 2. Batch CSV Processing

```bash
python naranjo.py batch --input sample.csv --output results.csv
```

### 3. Enterprise CLI

```bash
# Audit task evaluation
python cli.py audit --task-id TASK-001 --primary 28.5 --critical

# Batch processing
python cli.py batch -i sample.csv -o results.csv

# Verify audit trail
python cli.py verify-audit
```

### 4. REST API Server

```bash
# Direct
python cli.py serve --host 127.0.0.1 --port 8000

# Docker
docker-compose up --build
```

API Endpoints:
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `POST /api/audit` - Submit task evaluation
- `POST /api/chat` - Supervisor chat query
- `GET /api/audit/logs` - Audit trail with integrity verification

### 5. Simulation Benchmark

```bash
python simulator.py 1000
```

---

## Testing

```bash
pytest -v
```

---

## Security

- **Zero-PHI Outbound Guard:** AST and regex inspection blocking SSNs, MRNs, phone numbers, emails, and patient identifiers.
- **HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation.
- **Path Traversal Protection:** All file operations validate paths against traversal attacks.
- **No Hardcoded Secrets:** Audit key sourced from `AUDIT_SECRET_KEY` environment variable.

### Environment Variables

| Variable | Description | Required |
|:---------|:------------|:---------|
| `AUDIT_SECRET_KEY` | HMAC-SHA256 key for audit trail | Recommended |
| `MODEL_PROVIDER` | LLM provider (mock/ollama/claude/openai) | No (default: mock) |

Copy `.env.example` to `.env` and configure for production.

---

## License

MIT
