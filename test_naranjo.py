"""Tests for core Naranjo ADR scoring module."""
import os
import tempfile
import naranjo as m


def test_score_basic():
    """Basic score calculation with age and sex fields."""
    r = m.calculate_score({'age': 68, 'sex': 'M', 'cancer': 1})
    assert 'score' in r and 'tier' in r
    assert 'category' in r


def test_score_comparison():
    """Older patient with comorbidities scores higher than younger healthy."""
    r = m.calculate_score({'age': 68, 'sex': 'M', 'cancer': 1})
    r2 = m.calculate_score({'age': 30, 'sex': 'F'})
    assert r2['score'] <= r['score']


def test_score_with_factors():
    """Direct factor presence increases score."""
    r = m.calculate_score({'Hypotension': True, 'Tachycardia': True, 'Fever': True})
    assert r['score'] == 3
    assert r['tier'] == 'moderate'
    assert 'Hypotension' in r['detail']


def test_score_with_zero_factors():
    """No factors present yields zero score."""
    r = m.calculate_score({})
    assert r['score'] == 0
    assert r['tier'] == 'low'
    assert r['category'] == 'doubtful'


def test_score_with_string_values():
    """String 'yes'/'no' values are handled correctly."""
    r = m.calculate_score({'hypotension': 'yes', 'tachycardia': 'no', 'fever': '1'})
    assert r['score'] == 2


def test_score_with_integer_values():
    """Integer 1/0 values are handled correctly."""
    r = m.calculate_score({'hypotension': 1, 'tachycardia': 0, 'fever': 1, 'tachypnea': 1})
    assert r['score'] == 3


def test_score_invalid_input():
    """Non-dict input raises TypeError."""
    import pytest
    with pytest.raises(TypeError):
        m.calculate_score("not a dict")


def test_score_categories():
    """Score categories are correctly assigned."""
    # doubtful: score <= 0
    assert m.calculate_score({})['category'] == 'doubtful'
    # possible: score 1-4
    assert m.calculate_score({'Hypotension': 1, 'Tachycardia': 1})['category'] == 'possible'
    # probable: score 5-8 (all 5 factors = score 5)
    all_factors = {f: 1 for f, _ in m.FACTORS}
    r = m.calculate_score(all_factors)
    assert r['score'] == 5
    assert r['category'] == 'probable'


def test_assess_row():
    """assess_row processes CSV row dicts correctly."""
    row = {'patient_id': 'P001', 'hypotension': '1', 'tachycardia': '1', 'fever': '0'}
    r = m.assess_row(row)
    assert r['score'] == 2


def test_assess_row_invalid():
    """assess_row rejects non-dict input."""
    import pytest
    with pytest.raises(TypeError):
        m.assess_row("not a dict")


def test_process_csv():
    """process_csv reads input and writes scored output."""
    # Create a temporary input CSV
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        f.write('patient_id,hypotension,tachycardia,fever\n')
        f.write('P001,1,1,0\n')
        f.write('P002,0,0,0\n')
        inp = f.name

    out = inp.replace('.csv', '_out.csv')
    try:
        results = m.process_csv(inp, out)
        assert len(results) == 2
        assert results[0]['score'] == 2
        assert results[1]['score'] == 0
        assert os.path.exists(out)

        # Verify output CSV structure
        import csv
        with open(out, newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert 'score' in rows[0]
            assert 'tier' in rows[0]
            assert 'category' in rows[0]
    finally:
        os.unlink(inp)
        if os.path.exists(out):
            os.unlink(out)


def test_process_csv_missing_file():
    """process_csv raises FileNotFoundError for missing input."""
    import pytest
    with pytest.raises(FileNotFoundError):
        m.process_csv('/nonexistent/path/input.csv', '/tmp/output.csv')


def test_process_csv_null_bytes():
    """process_csv rejects paths with null bytes."""
    import pytest
    with pytest.raises(ValueError):
        m.process_csv('input\x00.csv', 'output.csv')


def test_cli_single():
    """CLI single command works."""
    result = m.main(['single', '--hypotension', '1', '--fever', '1'])
    assert result == 0


def test_cli_batch_missing_file():
    """CLI batch command returns error for missing file."""
    result = m.main(['batch', '--input', '/nonexistent/file.csv', '--output', '/tmp/out.csv'])
    assert result == 1


def test_cli_invalid_json():
    """CLI single with invalid JSON returns error."""
    result = m.main(['single', '--json', '{invalid json}'])
    assert result == 1


def test_normalize_value():
    """_normalize_value handles various types correctly."""
    assert m._normalize_value(True) is True
    assert m._normalize_value(1) is True
    assert m._normalize_value("yes") is True
    assert m._normalize_value("Y") is True
    assert m._normalize_value("present") is True
    assert m._normalize_value(False) is False
    assert m._normalize_value(0) is False
    assert m._normalize_value("no") is False
    assert m._normalize_value(None) is False
