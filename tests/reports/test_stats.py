import json
from pathlib import Path

import pytest

from phiexplorer.reports.stats import dataset_summary, organism_summary

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "sample_export.json"


@pytest.fixture
def export():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_dataset_summary(export):
    df = dataset_summary(export)
    counts = df["Count"]

    assert counts["Genes"] == 2
    assert counts["Interactions"] == 2
    assert counts["Interactions (unique)"] == 2
    assert counts["Pathogens"] == 1
    assert counts["Hosts"] == 1
    assert counts["Diseases"] == 1
    assert counts["Publications"] == 1
    assert counts["Pathogen-host interaction phenotype"] == 2
    assert counts["Pathogen phenotype"] == 1
    assert counts["Disease name"] == 1
    assert counts["GO Cellular Component"] == 1
    assert counts["Gene-for-gene phenotype"] == 0


def test_organism_summary(export):
    result = organism_summary(export, 90000, "Testus pathogenicus")
    assert result == {"genes": 2, "interactions": 2}
