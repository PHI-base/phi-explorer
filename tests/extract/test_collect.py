import json
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pytest

from phiexplorer.dereference import chain
from phiexplorer.extract import _collect

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "sample_export.json"


@pytest.fixture
def export():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def session(export):
    return next(iter(export["curation_sessions"].values()))


def test_new_base_gene_record_has_expected_fields():
    gd = _collect.new_base_gene_record()
    assert gd["uniprot_id"] is None
    assert gd["gene_name"] is None
    assert gd["product"] is None
    assert gd["phig_id"] is None
    for field in [
        "phi4_ids", "high_level_phenotypes", "pathogen_phenotype_terms",
        "host_species", "infected_tissues", "allele_types", "allele_names",
        "allele_descriptions", "pmids",
    ]:
        assert gd[field] == set()


def test_collect_gene_metadata(session):
    gene_data = defaultdict(_collect.new_base_gene_record)
    _collect.collect_gene_metadata(session, "Testus pathogenicus", gene_data)

    assert set(gene_data) == {"Q00001", "Q00002"}
    assert gene_data["Q00001"]["uniprot_id"] == "Q00001"
    assert gene_data["Q00001"]["gene_name"] == "geneA"
    assert gene_data["Q00001"]["product"] == "putative secreted effector protein"
    assert gene_data["Q00002"]["gene_name"] == "geneB"


def test_collect_allele_fields(session):
    gene_data = defaultdict(_collect.new_base_gene_record)
    allele_to_gene = _collect.collect_allele_fields(session, "Testus pathogenicus", gene_data)

    assert allele_to_gene == {
        "Q00001:sess0001-1": "Q00001",
        "Q00002:sess0001-1": "Q00002",
    }
    assert gene_data["Q00001"]["allele_types"] == {"deletion"}
    assert gene_data["Q00001"]["allele_names"] == {"geneAdelta"}
    assert gene_data["Q00001"]["allele_descriptions"] == {"full deletion"}
    assert gene_data["Q00002"]["allele_types"] == {"deletion"}


def test_collect_host_species(session):
    gene_data = defaultdict(_collect.new_base_gene_record)
    allele_to_gene = chain.allele_to_gene_map(session, "Testus pathogenicus")
    genotype_to_genes = chain.genotype_to_genes_map(session, 90000, allele_to_gene)
    metagenotype_to_genes = chain.metagenotype_to_genes_map(session, genotype_to_genes)
    taxid_to_name = chain.taxid_to_name_map(session)

    _collect.collect_host_species(session, metagenotype_to_genes, taxid_to_name, gene_data)

    assert gene_data["Q00001"]["host_species"] == {"Testus hostus"}
    assert gene_data["Q00002"]["host_species"] == {"Testus hostus"}


def test_apply_common_annotation_fields_phenotype_and_tissue(session):
    gd = _collect.new_base_gene_record()
    ann = session["annotations"][0]  # pathogen_host_interaction_phenotype, metagenotype-1
    _collect.apply_common_annotation_fields(ann, gd)

    assert gd["pmids"] == {"PMID:11111111"}
    assert gd["phi4_ids"] == {"PHI:1"}
    assert gd["high_level_phenotypes"] == {"loss of pathogenicity"}
    assert gd["infected_tissues"] == {"leaf"}


def test_apply_common_annotation_fields_pathogen_phenotype_term(session):
    gd = _collect.new_base_gene_record()
    ann = session["annotations"][2]  # pathogen_phenotype, term PHIPO:0000015
    _collect.apply_common_annotation_fields(ann, gd)

    assert gd["pathogen_phenotype_terms"] == {"PHIPO:0000015"}
    assert gd["pmids"] == {"PMID:11111111"}


def test_sort_by_phenotype_priority_orders_by_priority_then_id():
    df = pd.DataFrame([
        {"uniprot_id": "B", "high_level_phenotype": "unaffected pathogenicity"},
        {"uniprot_id": "A", "high_level_phenotype": "loss of pathogenicity"},
        {"uniprot_id": "C", "high_level_phenotype": ""},
    ])
    phenotype_cols = [
        "loss of pathogenicity",
        "reduced virulence",
        "unaffected pathogenicity",
        "increased virulence",
    ]

    sorted_df = _collect.sort_by_phenotype_priority(df, phenotype_cols)

    assert list(sorted_df["uniprot_id"]) == ["A", "B", "C"]


def test_sort_by_phenotype_priority_empty_dataframe_passthrough():
    df = pd.DataFrame(columns=["uniprot_id", "high_level_phenotype"])
    phenotype_cols = ["loss of pathogenicity"]

    result = _collect.sort_by_phenotype_priority(df, phenotype_cols)

    assert result.empty
