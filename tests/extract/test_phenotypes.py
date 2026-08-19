import json
from pathlib import Path

import pytest

from phiexplorer.extract.phenotypes import extract_protein_phenotypes

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "sample_export.json"


@pytest.fixture
def export():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_extract_protein_phenotypes(export):
    df = extract_protein_phenotypes(export, taxid=90000, sciname="Testus pathogenicus")

    assert len(df) == 2
    assert set(df["uniprot_id"]) == {"Q00001", "Q00002"}

    q1 = df[df["uniprot_id"] == "Q00001"].iloc[0]
    assert q1["high_level_phenotype"] == "loss of pathogenicity"
    assert bool(q1["phenotype: loss of pathogenicity"]) is True
    assert q1["infected_tissues"] == "leaf"
    assert q1["pathogen_phenotype_terms"] == "PHIPO:0000015"
    assert q1["host_species"] == "Testus hostus"
    assert q1["num_publications"] == 1
    assert q1["allele_synonyms"] == "geneA-KO"

    q2 = df[df["uniprot_id"] == "Q00002"].iloc[0]
    assert q2["high_level_phenotype"] == "unaffected pathogenicity"


def test_extract_protein_phenotypes_no_match(export):
    df = extract_protein_phenotypes(export, taxid=1, sciname="Nonexistent species")
    assert df.empty
