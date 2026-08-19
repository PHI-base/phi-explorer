import json
from pathlib import Path

import pytest

from phiexplorer.extract.effectors import extract_effector_proteins, is_effector

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "sample_export.json"


@pytest.fixture
def export():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_is_effector_by_keyword():
    is_eff, reasons = is_effector("putative secreted effector protein", [])
    assert is_eff
    assert any("effector" in r for r in reasons)
    assert any("secret" in r for r in reasons)


def test_is_effector_by_go_term():
    is_eff, reasons = is_effector("hypothetical protein", [("cellular_component", "GO:0005576")])
    assert is_eff
    assert any("GO:0005576" in r for r in reasons)


def test_is_effector_negative():
    is_eff, reasons = is_effector("hypothetical protein", [])
    assert not is_eff
    assert reasons == []


def test_extract_effector_proteins(export):
    df = extract_effector_proteins(export, taxid=90000, sciname="Testus pathogenicus")

    assert len(df) == 1
    assert df.iloc[0]["uniprot_id"] == "Q00001"
    assert "effector" in df.iloc[0]["effector_evidence"]
    assert df.iloc[0]["go_cellular_component"] == "GO:0005576"
