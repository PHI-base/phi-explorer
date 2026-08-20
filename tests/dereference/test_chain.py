import json
from pathlib import Path

import pytest

from phiexplorer.dereference import chain

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "sample_export.json"


@pytest.fixture
def export():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def session(export):
    return next(iter(export["curation_sessions"].values()))


def test_sessions_with_organism(export):
    sessions = list(chain.sessions_with_organism(export, "Testus pathogenicus"))
    assert len(sessions) == 1

    no_match = list(chain.sessions_with_organism(export, "Nonexistent species"))
    assert no_match == []


def test_genes_for_organism(session):
    genes = chain.genes_for_organism(session, "Testus pathogenicus")
    assert set(genes) == {"Q00001", "Q00002"}


def test_allele_to_gene_map(session):
    mapping = chain.allele_to_gene_map(session, "Testus pathogenicus")
    assert mapping == {
        "Q00001:sess0001-1": "Q00001",
        "Q00002:sess0001-1": "Q00002",
    }


def test_genotype_to_genes_map(session):
    allele_to_gene = chain.allele_to_gene_map(session, "Testus pathogenicus")
    mapping = chain.genotype_to_genes_map(session, 90000, allele_to_gene)
    assert mapping == {
        "sess0001-genotype-1": {"Q00001"},
        "sess0001-genotype-2": {"Q00002"},
    }


def test_metagenotype_to_genes_map(session):
    allele_to_gene = chain.allele_to_gene_map(session, "Testus pathogenicus")
    genotype_to_genes = chain.genotype_to_genes_map(session, 90000, allele_to_gene)
    mapping = chain.metagenotype_to_genes_map(session, genotype_to_genes)
    assert mapping == {
        "sess0001-metagenotype-1": {"Q00001"},
        "sess0001-metagenotype-2": {"Q00002"},
    }


def test_taxid_to_name_map(session):
    assert chain.taxid_to_name_map(session) == {
        90000: "Testus pathogenicus",
        90001: "Testus hostus",
    }


def test_host_species_for_metagenotype(session):
    taxid_to_name = chain.taxid_to_name_map(session)
    mg = session["metagenotypes"]["sess0001-metagenotype-1"]
    assert chain.host_species_for_metagenotype(session, mg, taxid_to_name) == "Testus hostus"


def test_resolve_annotation_gene_ids_metagenotype(session):
    allele_to_gene = chain.allele_to_gene_map(session, "Testus pathogenicus")
    genotype_to_genes = chain.genotype_to_genes_map(session, 90000, allele_to_gene)
    metagenotype_to_genes = chain.metagenotype_to_genes_map(session, genotype_to_genes)

    ann = session["annotations"][0]
    uids = chain.resolve_annotation_gene_ids(
        ann, metagenotype_to_genes, genotype_to_genes, "Testus pathogenicus"
    )
    assert uids == {"Q00001"}


def test_resolve_annotation_gene_ids_gene(session):
    ann = session["annotations"][4]
    uids = chain.resolve_annotation_gene_ids(ann, {}, {}, "Testus pathogenicus")
    assert uids == {"Q00001"}


def test_all_organisms(export):
    assert chain.all_organisms(export) == {
        90000: "Testus pathogenicus",
        90001: "Testus hostus",
    }


def test_resolve_organism_by_taxid(export):
    assert chain.resolve_organism(export, taxid=90000) == (90000, "Testus pathogenicus")


def test_resolve_organism_by_sciname(export):
    result = chain.resolve_organism(export, sciname="Testus pathogenicus")
    assert result == (90000, "Testus pathogenicus")


def test_resolve_organism_by_sciname_case_insensitive(export):
    result = chain.resolve_organism(export, sciname="testus PATHOGENICUS")
    assert result == (90000, "Testus pathogenicus")


def test_resolve_organism_both_given_consistent(export):
    result = chain.resolve_organism(export, taxid=90000, sciname="Testus pathogenicus")
    assert result == (90000, "Testus pathogenicus")


def test_resolve_organism_both_given_mismatched(export):
    with pytest.raises(ValueError, match="not 'Testus hostus'"):
        chain.resolve_organism(export, taxid=90000, sciname="Testus hostus")


def test_resolve_organism_unknown_taxid(export):
    with pytest.raises(ValueError, match="no organism with taxid 1 "):
        chain.resolve_organism(export, taxid=1)


def test_resolve_organism_unknown_sciname(export):
    with pytest.raises(ValueError, match="no organism named"):
        chain.resolve_organism(export, sciname="Nonexistent species")


def test_resolve_organism_neither_given(export):
    with pytest.raises(ValueError, match="must provide"):
        chain.resolve_organism(export)


def test_resolve_organism_ambiguous_sciname():
    """Defensive case: two taxids sharing one display name (shouldn't happen in
    real PHI-base data, but resolve_organism must not silently pick one)."""
    export = {
        "curation_sessions": {
            "sessA": {
                "organisms": {
                    "90000": {"full_name": "Testus pathogenicus", "role": "pathogen"},
                },
            },
            "sessB": {
                "organisms": {
                    "90002": {"full_name": "Testus pathogenicus", "role": "pathogen"},
                },
            },
        },
    }
    with pytest.raises(ValueError, match="matches multiple organisms"):
        chain.resolve_organism(export, sciname="Testus pathogenicus")
