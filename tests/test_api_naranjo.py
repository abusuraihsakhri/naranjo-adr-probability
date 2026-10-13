"""FastAPI scoring endpoint contract tests without network dependencies."""
import pytest
from fastapi import HTTPException
from agents.api import NaranjoRequest, api_naranjo

def test_naranjo_endpoint_scores_all_unknown():
    request = NaranjoRequest(responses={f"q{i}": "unknown" for i in range(1, 11)})
    output = api_naranjo(request)
    assert output["score"] == 0
    assert output["category"] == "doubtful"
    assert len(output["detail"]) == 10

def test_naranjo_endpoint_rejects_incomplete_case():
    with pytest.raises(HTTPException) as error:
        api_naranjo(NaranjoRequest(responses={"q1": "yes"}))
    assert error.value.status_code == 422
