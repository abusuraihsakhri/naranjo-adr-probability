"""Regression tests against the published ten-item Naranjo scoring table."""
import csv
import itertools
import json
import pytest
from naranjo import QUESTIONS, calculate_score, assess_row, process_csv, main

UNKNOWN = {f"q{i}": "unknown" for i in range(1, 11)}

def test_maximum_and_minimum():
    max_answers = {f"q{i}": "yes" for i in range(1, 11)}
    max_answers.update(q5="no", q6="no")
    positive = calculate_score(max_answers)
    assert positive["score"] == 13 and positive["category"] == "definite"
    negative = calculate_score(dict(UNKNOWN, q2="no", q4="no", q5="yes", q6="yes"))
    assert negative["score"] == -4 and negative["category"] == "doubtful"

def test_response_weights():
    for key, _, yes, no in QUESTIONS:
        for answer, expected in (("yes", yes), ("no", no), ("unknown", 0)):
            result = calculate_score(dict(UNKNOWN, **{key: answer}))
            assert result["detail"][key]["points"] == expected

@pytest.mark.parametrize("score,category", [(0,"doubtful"),(1,"possible"),(4,"possible"),(5,"probable"),(8,"probable"),(9,"definite")])
def test_thresholds(score, category):
    # Find a questionnaire response pattern realizing each score.
    for values in itertools.product(("yes","no","unknown"), repeat=10):
        answers = dict(zip((q[0] for q in QUESTIONS), values))
        result = calculate_score(answers)
        if result["score"] == score:
            assert result["category"] == category
            break
    else:
        pytest.fail("Expected score is unreachable")

def test_unknown_differs_from_no():
    assert calculate_score(UNKNOWN)["score"] == 0
    assert calculate_score(dict(UNKNOWN, q5="no"))["score"] == 2

def test_invalid_input_rejected():
    with pytest.raises(TypeError):
        calculate_score([])
    with pytest.raises(ValueError, match="Missing"):
        calculate_score({"q1": "yes"})
    with pytest.raises(ValueError, match="Invalid response"):
        calculate_score(dict(UNKNOWN, q1="1"))

def test_csv_roundtrip_and_cli(tmp_path, capsys):
    source, output = tmp_path/"input.csv", tmp_path/"output.csv"
    with source.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["case_id"] + list(UNKNOWN))
        writer.writeheader()
        writer.writerow({"case_id": "CASE-01", **UNKNOWN})
    assert process_csv(str(source), str(output))[0]["score"] == 0
    assert main(["batch", "--input", str(source), "--output", str(output)]) == 0
    with output.open(newline="") as file:
        row = next(csv.DictReader(file))
        assert row["category"] == "doubtful"
    assert assess_row({k.upper(): v for k, v in UNKNOWN.items()})["score"] == 0
    assert main(["single", "--json", json.dumps(UNKNOWN)]) == 0
    assert main(["single", "--q1", "yes"]) == 1
    assert "Missing Naranjo" in capsys.readouterr().err

def test_csv_malformed_does_not_create_output(tmp_path):
    source, output = tmp_path/"bad.csv", tmp_path/"output.csv"
    source.write_text("q1,q2\nyes,no\n")
    with pytest.raises(ValueError, match="Missing CSV columns"):
        process_csv(str(source), str(output))
    assert not output.exists()
    with pytest.raises(ValueError, match="different"):
        process_csv(str(source), str(source))
