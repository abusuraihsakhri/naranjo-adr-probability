"""Agent batch path and boolean coercion regression tests."""
from cli import main
import csv

def test_batch_false_flag_stays_false(tmp_path):
    src, dst = tmp_path/"input.csv", tmp_path/"output.csv"
    with src.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["task_id", "target_identifier", "primary_metric",
                                                "secondary_metric", "is_critical_flag"])
        writer.writeheader()
        writer.writerow({"task_id": "BATCH-01", "target_identifier": "KEY-01",
                         "primary_metric": "10", "secondary_metric": "3", "is_critical_flag": "False"})
    assert main(["batch", "-i", str(src), "-o", str(dst)]) == 0
    with dst.open(newline="") as f:
        row = next(csv.DictReader(f))
        assert row["overall_urgency"] == "ROUTINE"

def test_batch_rejects_invalid_flag_and_input_overwrite(tmp_path):
    src, dst = tmp_path/"input.csv", tmp_path/"output.csv"
    src.write_text("task_id,is_critical_flag\nTEST-01,sometimes\n")
    assert main(["batch", "-i", str(src), "-o", str(dst)]) == 1
    assert not dst.exists()
    assert main(["batch", "-i", str(src), "-o", str(src)]) == 1
