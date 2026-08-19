"""Dataset-wide and per-organism summary statistics, generalized from
James Seager's phibase5_stats.py (PHI5-data-mining-statistics) -
see docs/PORTING-NOTES.md.
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

from phiexplorer.dereference import chain


def _metagenotype_key(metagenotype: dict, session: dict) -> tuple:
    def genotype_key(genotype_id):
        genotype = session["genotypes"][genotype_id]
        alleles = tuple(
            locus_allele["id"]
            for locus in genotype["loci"]
            for locus_allele in locus
        )
        return (genotype["organism_taxonid"], genotype["organism_strain"], alleles)

    return (
        genotype_key(metagenotype["pathogen_genotype"]),
        genotype_key(metagenotype["host_genotype"]),
    )


def dataset_summary(export: dict) -> pd.DataFrame:
    """Dataset-wide counts: genes, interactions, pathogens, hosts,
    diseases, publications, and per-annotation-type counts.
    """
    annotation_counts: dict[str, int] = defaultdict(int)
    diseases, genes, publications = set(), set(), set()
    pathogens, hosts = set(), set()
    metagenotypes, metagenotypes_unique = set(), set()

    for session in export.get("curation_sessions", {}).values():
        publications.add(session["metadata"]["curation_pub_id"])

        for annotation in session.get("annotations", []):
            ann_type = annotation["type"]
            annotation_counts[ann_type] += 1
            if ann_type == "disease_name":
                diseases.add(annotation["term"])

        for gene_id in session.get("genes", {}):
            genes.add(gene_id)

        for mg in session.get("metagenotypes", {}).values():
            metagenotypes.add((mg["pathogen_genotype"], mg["host_genotype"]))
            metagenotypes_unique.add(_metagenotype_key(mg, session))

        for taxon_id, organism in session.get("organisms", {}).items():
            if organism["role"] == "pathogen":
                pathogens.add(taxon_id)
            elif organism["role"] == "host":
                hosts.add(taxon_id)

    return pd.DataFrame(
        {
            "Genes": len(genes),
            "Interactions": len(metagenotypes),
            "Interactions (unique)": len(metagenotypes_unique),
            "Pathogens": len(pathogens),
            "Hosts": len(hosts),
            "Diseases": len(diseases),
            "Publications": len(publications),
            "Pathogen-host interaction phenotype": annotation_counts["pathogen_host_interaction_phenotype"],
            "Gene-for-gene phenotype": annotation_counts["gene_for_gene_phenotype"],
            "Pathogen phenotype": annotation_counts["pathogen_phenotype"],
            "Host phenotype": annotation_counts["host_phenotype"],
            "GO Biological Process": annotation_counts["biological_process"],
            "GO Molecular Function": annotation_counts["molecular_function"],
            "GO Cellular Component": annotation_counts["cellular_component"],
            "Disease name": annotation_counts["disease_name"],
            "Physical interaction": annotation_counts["physical_interaction"],
            "Post-translational modification": annotation_counts["post_translational_modification"],
            "Wild-type protein expression": annotation_counts["wt_protein_expression"],
            "Wild-type RNA expression": annotation_counts["wt_rna_expression"],
        },
        index=["Count"],
    ).transpose().rename_axis("Feature")


def organism_summary(export: dict, taxid: int, sciname: str) -> dict[str, int]:
    """Gene and unique-interaction counts for a single organism."""
    genes: set = set()
    interactions: set = set()

    for session in chain.sessions_with_organism(export, sciname):
        for gene_id, gene in session.get("genes", {}).items():
            if gene.get("organism") == sciname:
                genes.add(gene_id)

        for mg in session.get("metagenotypes", {}).values():
            pathogen_genotype = session["genotypes"][mg["pathogen_genotype"]]
            if pathogen_genotype["organism_taxonid"] != taxid:
                continue
            interactions.add(_metagenotype_key(mg, session))

    return {"genes": len(genes), "interactions": len(interactions)}
