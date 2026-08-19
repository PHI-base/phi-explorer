"""Shared gene-record collection helpers used by extract/phenotypes.py and
extract/effectors.py. Factored out because both modules' collector functions
were ~87% identical - see docs/PORTING-NOTES.md.

Internal module (leading underscore): not part of the public phiexplorer API.
"""
from __future__ import annotations

import pandas as pd

from phiexplorer.dereference import chain

INFECTIVE_ABILITY_TERMS = {
    "PHIPO:0000004": "unaffected pathogenicity",
    "PHIPO:0000010": "loss of pathogenicity",
    "PHIPO:0000014": "increased virulence",
    "PHIPO:0000015": "reduced virulence",
}


def new_base_gene_record() -> dict:
    """Fields common to every extract/ gene record. Callers add their own
    module-specific extra fields via dict assignment after calling this."""
    return {
        "uniprot_id": None,
        "gene_name": None,
        "product": None,
        "phig_id": None,
        "phi4_ids": set(),
        "high_level_phenotypes": set(),
        "pathogen_phenotype_terms": set(),
        "host_species": set(),
        "infected_tissues": set(),
        "allele_types": set(),
        "allele_names": set(),
        "allele_descriptions": set(),
        "pmids": set(),
    }


def collect_gene_metadata(session: dict, sciname: str, gene_data: dict[str, dict]) -> None:
    """Populate uniprot_id/gene_name/product/phig_id for genes of `sciname`
    in this session. Mutates `gene_data` in place."""
    genes = chain.genes_for_organism(session, sciname)
    for uid, gene in genes.items():
        gd = gene_data[uid]
        if gd["uniprot_id"] is None:
            gd["uniprot_id"] = uid
            ud = gene.get("uniprot_data", {})
            gd["gene_name"] = ud.get("name")
            gd["product"] = ud.get("product")
            gd["phig_id"] = gene.get("phig_id")


def collect_allele_fields(session: dict, sciname: str, gene_data: dict[str, dict]) -> dict[str, str]:
    """Populate allele_types/allele_names/allele_descriptions for genes of
    `sciname` in this session. Mutates `gene_data` in place. Returns the
    allele_id -> uniprot_id map (chain.allele_to_gene_map's result), which
    callers reuse for their own extra per-allele work (e.g. synonyms,
    expression levels)."""
    allele_to_gene = chain.allele_to_gene_map(session, sciname)
    for allele_id, allele in session.get("alleles", {}).items():
        uid = allele_to_gene.get(allele_id)
        if uid is None:
            continue
        gd = gene_data[uid]
        atype = allele.get("allele_type")
        if atype and atype not in ("wild type", "wild_type"):
            gd["allele_types"].add(atype)
        name = allele.get("name")
        if name:
            gd["allele_names"].add(name)
        description = allele.get("description")
        if description:
            gd["allele_descriptions"].add(description)
    return allele_to_gene


def collect_host_species(
    session: dict,
    metagenotype_to_genes: dict[str, set[str]],
    taxid_to_name: dict[int, str],
    gene_data: dict[str, dict],
) -> None:
    """Populate host_species for genes covered by each metagenotype in this
    session. Mutates `gene_data` in place."""
    for mg_id, mg in session.get("metagenotypes", {}).items():
        uids = metagenotype_to_genes.get(mg_id)
        if not uids:
            continue
        host_name = chain.host_species_for_metagenotype(session, mg, taxid_to_name)
        if host_name:
            for uid in uids:
                gene_data[uid]["host_species"].add(host_name)


def apply_common_annotation_fields(ann: dict, gd: dict) -> None:
    """Mutate one gene's record for the fields common to phenotype and
    effector extraction, given one annotation already resolved to that gene:
    phi4_ids, pmids, high_level_phenotypes, infected_tissues,
    pathogen_phenotype_terms."""
    pmid = ann.get("publication")
    if pmid:
        gd["pmids"].add(pmid)
    for p4 in ann.get("phi4_id", []):
        gd["phi4_ids"].add(p4)

    ann_type = ann.get("type")
    if ann_type == "pathogen_host_interaction_phenotype":
        for ext in ann.get("extension", []):
            if ext.get("relation") == "infective_ability":
                label = ext.get("rangeDisplayName") or INFECTIVE_ABILITY_TERMS.get(
                    ext.get("rangeValue"), ext.get("rangeValue")
                )
                gd["high_level_phenotypes"].add(label)
            elif ext.get("relation") == "infects_tissue":
                tissue = ext.get("rangeDisplayName")
                if tissue:
                    gd["infected_tissues"].add(tissue)
    elif ann_type == "pathogen_phenotype":
        term = ann.get("term")
        if term:
            gd["pathogen_phenotype_terms"].add(term)


def sort_by_phenotype_priority(df: pd.DataFrame, phenotype_cols: list[str]) -> pd.DataFrame:
    """Sort a gene-record DataFrame by phenotype priority (loss of
    pathogenicity first, ..., no-phenotype-recorded last), then by
    uniprot_id. `df` must have a "high_level_phenotype" column. Returns
    `df` unchanged if it's empty."""
    if df.empty:
        return df

    def phenotype_sort_key(hlp_str: str) -> int:
        if not hlp_str:
            return len(phenotype_cols) + 1
        for i, p in enumerate(phenotype_cols):
            if p in hlp_str:
                return i
        return len(phenotype_cols)

    df = df.copy()
    df["_sort"] = df["high_level_phenotype"].map(phenotype_sort_key)
    df = df.sort_values(["_sort", "uniprot_id"]).drop(columns="_sort").reset_index(drop=True)
    return df
