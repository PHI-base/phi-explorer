"""Protein-level phenotype extraction, generalized from James Seager's
fg_protein_phenotypes.py (PHI5-zenodo-datamining) - see docs/PORTING-NOTES.md.
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

from phiexplorer.dereference import chain

INFECTIVE_ABILITY_TERMS = {
    "PHIPO:0000004": "unaffected pathogenicity",
    "PHIPO:0000010": "loss of pathogenicity",
    "PHIPO:0000014": "increased virulence",
    "PHIPO:0000015": "reduced virulence",
}

PHENOTYPE_COLS = [
    "loss of pathogenicity",
    "reduced virulence",
    "unaffected pathogenicity",
    "increased virulence",
]


def _new_gene_record() -> dict:
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
        "allele_synonyms": set(),
        "expression_levels": set(),
        "pmids": set(),
    }


def _collect_gene_data(export: dict, taxid: int, sciname: str) -> dict[str, dict]:
    gene_data: dict[str, dict] = defaultdict(_new_gene_record)

    for session in chain.sessions_with_organism(export, sciname):
        genes = chain.genes_for_organism(session, sciname)
        for uid, gene in genes.items():
            gd = gene_data[uid]
            if gd["uniprot_id"] is None:
                gd["uniprot_id"] = uid
                ud = gene.get("uniprot_data", {})
                gd["gene_name"] = ud.get("name")
                gd["product"] = ud.get("product")
                gd["phig_id"] = gene.get("phig_id")

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
            for synonym in allele.get("synonyms", []):
                if synonym:
                    gd["allele_synonyms"].add(synonym)

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
        for mg_id, mg in session.get("metagenotypes", {}).items():
            uids = metagenotype_to_genes.get(mg_id)
            if not uids:
                continue
            host_name = chain.host_species_for_metagenotype(session, mg, taxid_to_name)
            if host_name:
                for uid in uids:
                    gene_data[uid]["host_species"].add(host_name)

        for ann in session.get("annotations", []):
            uids = chain.resolve_annotation_gene_ids(
                ann, metagenotype_to_genes, genotype_to_genes, sciname
            )
            if not uids:
                continue

            ann_type = ann.get("type")
            pmid = ann.get("publication")
            phi4_ids = ann.get("phi4_id", [])

            for uid in uids:
                gd = gene_data[uid]
                if pmid:
                    gd["pmids"].add(pmid)
                for p4 in phi4_ids:
                    gd["phi4_ids"].add(p4)

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
    if df.empty:
        return df

    def phenotype_sort_key(hlp_str: str) -> int:
        if not hlp_str:
            return len(PHENOTYPE_COLS) + 1
        for i, p in enumerate(PHENOTYPE_COLS):
            if p in hlp_str:
                return i
        return len(PHENOTYPE_COLS)

    df["_sort"] = df["high_level_phenotype"].map(phenotype_sort_key)
    df = df.sort_values(["_sort", "uniprot_id"]).drop(columns="_sort").reset_index(drop=True)
    return df


def extract_protein_phenotypes(export: dict, taxid: int, sciname: str) -> pd.DataFrame:
    """Extract per-protein phenotype data for `sciname` (NCBI taxon `taxid`).

    Generalized from fg_protein_phenotypes.py - see docs/PORTING-NOTES.md.
    """
    gene_data = _collect_gene_data(export, taxid, sciname)
    return _build_dataframe(gene_data)
