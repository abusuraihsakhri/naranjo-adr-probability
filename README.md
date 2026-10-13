# Naranjo ADR Probability Scale

A ten-question adverse drug reaction (ADR) causality questionnaire with a standalone browser calculator, Python library/CLI, CSV batch scoring, and a FastAPI endpoint.

The questionnaire uses the published Naranjo weights. Each answer is **Yes**, **No**, or **Do not know** (0 points). The total can range from **−4 to +13**, with conventional interpretations:

| Total | Category |
|---|---|
| ≤0 | Doubtful |
| 1–4 | Possible |
| 5–8 | Probable |
| ≥9 | Definite |

These labels describe structured causality assessment, **not** adverse-event severity, a calibrated percentage probability, or a management recommendation. Clinical judgment is required. Never perform unsafe rechallenge or placebo exposure merely to complete a questionnaire.

## Browser calculator

Open `docs/index.html` in a modern browser, or use the GitHub Pages deployment when available. Select a response to each question, calculate the category, and optionally export the answers and score as CSV or print the assessment.

All browser calculations use native JavaScript. No Python runtime, external CDN, backend, personal identifiers, cookies, analytics, or browser storage is required. Input stays in the current browser tab unless the user exports or prints it. The same calculator is in `web/index.html`.

## Python installation and use

Requires Python **3.10+**.

```bash
python -m pip install -e ".[dev]"
python -m pytest -q

# Ten-item JSON assessment
python naranjo.py single --json '{"q1":"yes","q2":"yes","q3":"unknown","q4":"unknown","q5":"no","q6":"unknown","q7":"unknown","q8":"yes","q9":"unknown","q10":"yes"}'

# Score the included CSV example
python naranjo.py batch --input sample.csv --output results.csv
```

CSV inputs require columns `q1` to `q10` (case-insensitive), each containing `yes`, `no`, or `unknown`. Additional columns such as `case_id` are retained. Missing or ambiguous responses cause validation errors rather than implicit “No” scores.

## REST API

Start the optional FastAPI server with:

```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

Use `POST /api/naranjo` with a JSON body containing `responses`, a mapping of `q1` through `q10`. The response includes the numeric score, category, and per-question points. FastAPI exposes interactive schema documentation at `/docs`.

The existing `cli.py audit/chat/batch`, `agents/`, `simulator.py`, and `enrichment.py` provide *separate demonstration operations workflows*. Their generic metrics, heuristics, mock conversational replies, and threshold alerts **are not Naranjo causality scoring and are not validated for clinical decision-making**.

## Security and privacy

The browser calculator transmits nothing. The optional API processes data server-side: avoid identifiable clinical data without appropriate infrastructure, access controls, and a privacy review. The backend includes **best-effort pattern-based identifier screening**, not comprehensive de-identification or a HIPAA compliance guarantee. The HMAC audit chain is **in memory**, uses a random ephemeral key by default, and does not persist across restarts. Set `AUDIT_SECRET_KEY` securely for a stable signing key; never commit secrets.

The GitHub Actions workflow tests Python 3.10–3.12 and checks the browser JavaScript. A separate Pages workflow deploys `docs/` when GitHub Pages is enabled.

## Reference and limitations

Naranjo CA et al. *A method for estimating the probability of adverse drug reactions.* Clin Pharmacol Ther. 1981;30(2):239–245. The [NIH/NLM LiverTox table](https://www.ncbi.nlm.nih.gov/books/NBK548069/table/Narajo.Tc/) gives the official 10-item response weights.

This tool does not establish causation and does not replace specialty-specific assessment methods or clinical review.

## License

MIT — see [LICENSE](LICENSE).
