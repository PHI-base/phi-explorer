"""Protein-level phenotype extraction, generalized from James Seager's
fg_protein_phenotypes.py (PHI5-zenodo-datamining) - see docs/PORTING-NOTES.md.
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

from phiexplorer.dereference import chain
from phiexplorer.extract import _collect

INFECTIVE_ABILITY_TERMS = _collect.INFECTIVE_ABILITY_TERMS

PHENOTYPE_COLS = [
    "loss of pathogenicity",
    "reduced virulence",
    "unaffected pathogenicity",
    "increased virulence",
]


def _new_gene_record() -> dict:
    gd = _collect.new_base_gene_record()
    gd["allele_synonyms"] = set()
    gd["expression_levels"] = set()
    return gd


def _collect_gene_data(export: dict, taxid: int, sciname: str) -> dict[str, dict]:
    gene_data: dict[str, dict] = defaultdict(_new_gene_record)

    for session in chain.sessions_with_organism(export, sciname):
        _collect.collect_gene_metadata(session, sciname, gene_data)

        allele_to_gene = _collect.collect_allele_fields(session, sciname, gene_data)
        for allele_id, allele in session.get("alleles", {}).items():
            uid = allele_to_gene.get(allele_id)
            if uid is None:
                continue
            for synonym in allele.get("synonyms", []):
                if synonym:
                    gene_data[uid]["allele_synonyms"].add(synonym)

        genotype_to_genes = chain.genotype_to_genes_map(session, taxid, allele_to_gene)
        for geno_id, geno in session.get("genotypes", {}).items():
            uids = genotype_to_genes.get(geno_id)
            if not uids:
                continue
            for locus in geno.get("loci", []):
                for locus_allele in locus:
                    expression = locus_allele.get("expression")
                    if expression and expression != "Not assayed":
                        allele_uid = allele_to_gene.get(locus_allele.get("id"))
                        if allele_uid:
                            gene_data[allele_uid]["expression_levels"].add(expression)

        metagenotype_to_genes = chain.metagenotype_to_genes_map(session, genotype_to_genes)
        taxid_to_name = chain.taxid_to_name_map(session)
        _collect.collect_host_species(session, metagenotype_to_genes, taxid_to_name, gene_data)

        for ann in session.get("annotations", []):
            uids = chain.resolve_annotation_gene_ids(
                ann, metagenotype_to_genes, genotype_to_genes, sciname
            )
            if not uids:
                continue
            for uid in uids:
                _collect.apply_common_annotation_fields(ann, gene_data[uid])

    return dict(gene_data)


def _build_dataframe(gene_data: dict[str, dict]) -> pd.DataFrame:
    rows = []
    for gd in gene_data.values():
        if gd["uniprot_id"] is None:
            continue
        hlp = gd["high_level_phenotypes"]
        rows.append({
            "uniprot_id": gd["uniprot_id"],
            "gene_name": gd["gene_name"] or "",
            "product": gd["product"] or "",
            "phig_id": gd["phig_id"] or "",
            "phi4_ids": "; ".join(sorted(gd["phi4_ids"])),
            "high_level_phenotype": "; ".join(sorted(hlp)),
            **{f"phenotype: {p}": p in hlp for p in PHENOTYPE_COLS},
            "pathogen_phenotype_terms": "; ".join(sorted(gd["pathogen_phenotype_terms"])),
            "host_species": "; ".join(sorted(gd["host_species"])),
            "infected_tissues": "; ".join(sorted(gd["infected_tissues"])),
            "allele_types": "; ".join(sorted(gd["allele_types"])),
            "allele_names": "; ".join(sorted(gd["allele_names"])),
            "allele_descriptions": "; ".join(sorted(gd["allele_descriptions"])),
            "allele_synonyms": "; ".join(sorted(gd["allele_synonyms"])),
            "expression_levels": "; ".join(sorted(gd["expression_levels"])),
            "num_publications": len(gd["pmids"]),
            "pmids": "; ".join(sorted(gd["pmids"])),
        })

    df = pd.DataFrame(rows)
    return _collect.sort_by_phenotype_priority(df, PHENOTYPE_COLS)


def extract_protein_phenotypes(export: dict, taxid: int, sciname: str) -> pd.DataFrame:
    """Extract per-protein phenotype data for `sciname` (NCBI taxon `taxid`).

    Generalized from fg_protein_phenotypes.py - see docs/PORTING-NOTES.md.
    """
    gene_data = _collect_gene_data(export, taxid, sciname)
    return _build_dataframe(gene_data)
