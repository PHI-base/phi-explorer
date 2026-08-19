import json
from pathlib import Path

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_export.json"


def test_fixture_loads_and_has_expected_shape():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        export = json.load(f)

    assert export["schema_version"] == 1
    sessions = export["curation_sessions"]
    assert len(sessions) == 1

    session = next(iter(sessions.values()))
    assert len(session["genes"]) == 2
    assert len(session["organisms"]) == 2
    assert len(session["annotations"]) == 5
