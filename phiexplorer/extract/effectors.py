"""Effector protein identification, generalized from James Seager's
fg_effector_proteins.py (PHI5-zenodo-datamining) - see docs/PORTING-NOTES.md.
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

from phiexplorer.dereference import chain
from phiexplorer.extract import _collect
from phiexplorer.extract.phenotypes import PHENOTYPE_COLS

EFFECTOR_KEYWORDS = ["effector", "avirulence", "avr", "virulence factor"]

SECRETION_KEYWORDS = ["secret", "extracellular", "signal peptide", "small secreted"]

EFFECTOR_GO_TERMS = {
    "GO:0005576": "extracellular region",
    "GO:0005615": "extracellular space",
    "GO:0030446": "hyphal cell wall",
    "GO:0009405": "pathogenesis",
    "GO:0052031": "modulation by symbiont of host defense response",
    "GO:0052200": "response to host immune response",
    "GO:0140404": "pathogen-associated molecular pattern",
}

_GO_FIELD_BY_TYPE = {
    "biological_process": "go_biological_process",
    "molecular_function": "go_molecular_function",
    "cellular_component": "go_cellular_component",
}


def is_effector(product: str, annotation_terms: list[tuple[str, str]]) -> tuple[bool, list[str]]:
    """Determine effector status from a product name and (ann_type, term) pairs.

    Returns (is_effector, reasons).
    """
    reasons = []
    product_lower = (product or "").lower()

    for keyword in EFFECTOR_KEYWORDS:
        if keyword in product_lower:
            reasons.append(f"Product contains '{keyword}': {product}")

    for keyword in SECRETION_KEYWORDS:
        if keyword in product_lower:
            reasons.append(f"Secreted protein ('{keyword}'): {product}")

    for ann_type, term in annotation_terms:
        if term in EFFECTOR_GO_TERMS:
            reasons.append(f"GO {ann_type}: {term} ({EFFECTOR_GO_TERMS[term]})")

    return len(reasons) > 0, reasons


def _new_gene_record() -> dict:
    gd = _collect.new_base_gene_record()
    gd["go_biological_process"] = set()
    gd["go_molecular_function"] = set()
    gd["go_cellular_component"] = set()
    return gd


def _collect_gene_data(export: dict, taxid: int, sciname: str) -> tuple[dict[str, dict], dict[str, list]]:
    gene_data: dict[str, dict] = defaultdict(_new_gene_record)
    gene_annotations: dict[str, list] = defaultdict(list)

    for session in chain.sessions_with_organism(export, sciname):
        _collect.collect_gene_metadata(session, sciname, gene_data)
        allele_to_gene = _collect.collect_allele_fields(session, sciname, gene_data)

        genotype_to_genes = chain.genotype_to_genes_map(session, taxid, allele_to_gene)
        metagenotype_to_genes = chain.metagenotype_to_genes_map(session, genotype_to_genes)
        taxid_to_name = chain.taxid_to_name_map(session)
        _collect.collect_host_species(session, metagenotype_to_genes, taxid_to_name, gene_data)

        for ann in session.get("annotations", []):
            uids = chain.resolve_annotation_gene_ids(
                ann, metagenotype_to_genes, genotype_to_genes, sciname
            )
            if not uids:
                continue

            ann_type = ann.get("type")
            term = ann.get("term")

            for uid in uids:
                gene_annotations[uid].append(ann)
                gd = gene_data[uid]
                _collect.apply_common_annotation_fields(ann, gd)
                if ann_type in _GO_FIELD_BY_TYPE and term:
                    gd[_GO_FIELD_BY_TYPE[ann_type]].add(term)

    return dict(gene_data), dict(gene_annotations)


def _build_dataframe(effector_data: dict[str, dict]) -> pd.DataFrame:
    rows = []
    for gd in effector_data.values():
        hlp = gd["high_level_phenotypes"]
        rows.append({
            "uniprot_id": gd["uniprot_id"],
            "gene_name": gd["gene_name"] or "",
            "product": gd["product"] or "",
            "phig_id": gd["phig_id"] or "",
            "effector_evidence": " | ".join(gd["effector_evidence"]),
            "phi4_ids": "; ".join(sorted(gd["phi4_ids"])),
            "high_level_phenotype": "; ".join(sorted(hlp)),
            **{f"phenotype: {p}": p in hlp for p in PHENOTYPE_COLS},
            "pathogen_phenotype_terms": "; ".join(sorted(gd["pathogen_phenotype_terms"])),
            "go_biological_process": "; ".join(sorted(gd["go_biological_process"])),
            "go_molecular_function": "; ".join(sorted(gd["go_molecular_function"])),
            "go_cellular_component": "; ".join(sorted(gd["go_cellular_component"])),
            "host_species": "; ".join(sorted(gd["host_species"])),
            "infected_tissues": "; ".join(sorted(gd["infected_tissues"])),
            "allele_types": "; ".join(sorted(gd["allele_types"])),
            "allele_names": "; ".join(sorted(gd["allele_names"])),
            "allele_descriptions": "; ".join(sorted(gd["allele_descriptions"])),
            "num_publications": len(gd["pmids"]),
            "pmids": "; ".join(sorted(gd["pmids"])),
        })

    df = pd.DataFrame(rows)
    return _collect.sort_by_phenotype_priority(df, PHENOTYPE_COLS)


def extract_effector_proteins(export: dict, taxid: int, sciname: str) -> pd.DataFrame:
    """Extract effector/secreted proteins for `sciname` (NCBI taxon `taxid`).

    Generalized from fg_effector_proteins.py - see docs/PORTING-NOTES.md.
    """
    gene_data, gene_annotations = _collect_gene_data(export, taxid, sciname)

    for uid, gd in gene_data.items():
        annotation_terms = [
            (ann.get("type"), ann.get("term"))
            for ann in gene_annotations.get(uid, [])
            if ann.get("term")
        ]
        is_eff, reasons = is_effector(gd["product"], annotation_terms)
        gd["is_effector"] = is_eff
        gd["effector_evidence"] = reasons

    effector_data = {uid: gd for uid, gd in gene_data.items() if gd.get("is_effector")}
    return _build_dataframe(effector_data)
